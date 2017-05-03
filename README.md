# Website hosting on S3 with Cloudfront as CDN
For hosting a website on s3 using custum domains and TLS certificates for delivering it through https with the help of cloudfront.

Wraps alls the setup step into an easy to use role, which takes a few arguments and takes care of the rest.
Needs Ansible 2.2.0 or newer.

## Requirements
Needs the Ansible cloudfront module which is not relased yet, but copied into this repo in `files/cloudfront.py`.
So copy that module to your projects (that includes this role) module folder, commonly thats `./library/`.

## Role Variables

## Dependencies
Depends on not other Ansible role.

## Example Playbook
Use the role in your existing playbook like this:

    - hosts: servers
      roles:
         - { role: mediapeers.s3-website-hosting, domain: test.domain.com }

## License
BSD

## Author Information
Stefan Horning <horning@mediapeers.com>
