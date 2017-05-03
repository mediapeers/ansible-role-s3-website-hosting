[![Build Status](https://travis-ci.org/mediapeers/ansible-role-s3-website-hosting.svg?branch=master)](https://travis-ci.org/mediapeers/ansible-role-s3-website-hosting)

# Website hosting on S3 with Cloudfront as CDN
For hosting a website on s3 using custum domains and TLS certificates for delivering it through https with the help of cloudfront.

Wraps alls the setup step into an easy to use role, which takes a few arguments and takes care of the rest.
Needs Ansible 2.2.0 or newer.

## Requirements
Needs the Ansible cloudfront module which is not relased yet, but copied into this repo in `files/cloudfront.py`.
So copy that module to your projects (that includes this role) module folder, commonly thats `./library/`.

Also you need a working DNS zone in Route53 and working ACM ceritificates for the domains you want to use.

## Role Variables
The following variables can be set:

`s3_website_bucket_name: 'my-website-s3-bucket'` - Set your own bucket name. Needs overwriting!
`s3_website_bucket_region: 'us-east-1'` - Set your buckets region, defaults to us-east-1
`s3_website_alias_domain_names: ['custom-domain.org']` - Set your the domain(s) your Wedbsite should be reachable under. Needs overwriting!
`s3_website_certificate_arn: 'tls-certificate-arn-for-cloudwatch'` - Set the TLS certificate you already setup in ACM for the domains. Use the Certificates ARN here. Needed for HTTPs to work!
`s3_website_root_object: 'index.html'` - Root document for your website. Defaults to index.html

# Root documents for your website:
s3_website_root_object: 'index.html'
## Dependencies
Depends on not other Ansible role.

## Example Playbook
Use the role in your existing playbook like this:

    - hosts: localhost
      vars:
        s3_website_bucket_name: 'my-fancy-frontend'
        s3_website_alias_domain_names: 'my-fancy-frontend.com'
        s3_website_certificate_arn: 'arn:aws:acm:us-east-1:1230000000000:certificate/64089f32-b35a-4cdb-x301-2bc982d4630x'
      roles:
         - mediapeers.s3-website-hosting

## License
BSD

## Author Information
Stefan Horning <horning@mediapeers.com>
