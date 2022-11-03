---

- name: patching
  hosts: all
  gather_facts: yes

  vars:
    # By default do full update.
    patching: full_update
    duration: 3600
    icinga_api_user: awx
    icinga_api_pass: !vault |
          $ANSIBLE_VAULT;1.1;AES256
          30666335353434626236623130666332356433303330323063643063316166306161383464636166
          6339363538656635366162333465366334323433303530620a663962643632386161356333306639
          65636162346565346164323035386230633233373961626462386262323636343036376134623363
          3839326163383738350a626264363338313537346561313436313832393964643665363832326436
          32306338323934663163363031376334306166376265336231633563323239393233

  environment:
    https_proxy: "{{ https_proxy }}"

  tasks:

  - name: Check if there are available some updates
    shell: "yum check-update -y"
    register: yum_check_update
    ignore_errors: yes
    when: patching == "full_update"

  - name: Check if there are available some security updates
    shell: "yum check-update --security -y"
    register: yum_check_update_security
    ignore_errors: yes
    when: patching == "just_security"

  - name: Patching
    block:
      - name: Schedule downtime using Icinga2 API
        delegate_to: localhost
        uri:
          url: "https://{{ icinga_host }}:5665/v1/actions/schedule-downtime"
          user: "{{ icinga_api_user }}"
          password: "{{ icinga_api_pass }}"
          validate_certs: false
          method: POST
          body_format: json
          headers:
            Accept: "application/json"
          status_code: 200
          body: '{ "type": "Host", "filter":"host.name==\"{{ ansible_hostname | upper }}\"", "author": "AWX", "comment": "OS patching", "notify": true, "pretty": true, "start_time": {{ ansible_date_time.epoch }}, "end_time": "{{ ansible_date_time.epoch | int + duration | int }}", "duration": {{ duration }}, "fixed": false }'
 

      - name: Update all packages
        yum:
          name: "{{ patch_pkgs | default('*') }}"
          state: latest
        environment:
          ACCEPT_EULA: "y"
        when:
          - exclude_pkgs is undefined
          - patching == "full_update"


      - name: Update all packages and exclude "{{ exclude_pkgs }}"
        yum:
          name: "{{ patch_pkgs | default('*') }}"
          exclude: "{{ exclude_pkgs }}"
          state: latest
        environment:
          ACCEPT_EULA: "y"
        when: exclude_pkgs is defined


      - name: Update just security flaws
        yum:
          name: "*"
          security: yes
          state: latest
        environment:
          ACCEPT_EULA: "y"
        when:
          - exclude_pkgs is undefined
          - patching == "just_security"


      - name: Reboot server if necessary
        command: shutdown -r now "Reboot for automatic patching"
        async: 30
        poll: 0


      - name: Wait then the system boot up
        wait_for_connection:
          connect_timeout: 20
          sleep: 5
          delay: 5
          timeout: 300


      - name: Get uptime
        command: uptime
        register: uptime_output


      - name: Print uptime
        debug:
          msg: "{{ uptime_output.stdout }}"

    when:
      - ansible_distribution == "CentOS"
      - yum_check_update is defined and yum_check_update.rc | default('') != 0
      - yum_check_update_security is defined and yum_check_update_security.rc | default('') != 0