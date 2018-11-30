[![Build Status](https://travis-ci.com/mediapeers/ansible-role-s3-website-hosting.svg?branch=master)](https://travis-ci.com/mediapeers/ansible-role-s3-website-hosting)

# Website hosting on S3 with Cloudfront as CDN
Role for static website hosting on AWS using S3 for storage and CloudFront for distribution over HTTPs.

This role sets up the S3 bucket with the right configuration and then creates a CloudFront distribution using that bucket as a origin.
Takes care of bucket permissions, CloudFront origin config and TLS setup, using given CNAMEs and ACM (AWS certificate manager) TLS certificate.

Needs Ansible 2.5 or newer for the `cloudfront_distribution` module.

## Requirements
Needs a working DNS zone in Route53 and working ACM certificates for the domains you want to use.

## Role Variables
The following variables can be set:

- `s3_website_bucket_name: 'my-website-s3-bucket'` - Set your own bucket name. **Needs overwriting!**
- `s3_website_bucket_region: 'us-east-1'` - Set your buckets region, defaults to us-east-1
- `s3_website_alias_domain_names: ['custom-domain.org']` - Set your the domain(s) your Wedbsite should be reachable under. **Needs overwriting!**
- `s3_website_certificate_arn: 'tls-certificate-arn-for-cloudwatch'` - Set the TLS certificate you already setup in ACM for the domains. Use the Certificates ARN here. **Needed for HTTPs to work!**
- `s3_website_create_dns_record: true` - Set false to not create a Route53 DNS record, like when domain is managed elsewhere
- `s3_website_root_object: 'index.html'` - Root document for your website. Defaults to index.html
- `s3_website_caching_max_ttl: 2592000` -  max seconds items can stay in the CloudFront cache (AWS defaults to 365 here, this role to 30)
- `s3_website_caching_default_ttl: 86400` - seconds after which the origin is checked for a change (default to 1 day, also AWS default)
- `s3_website_price_class: PriceClass_100` - price class for CloudFront distribution
- `s3_website_cloudfront_lambda_functions: []` - Add dicts to this list you want included into the Cloudfront config (Lambda@Edge function). Each dict item should keys `lambda_function_arn` (with a valid Lambda ARN) and the `event_type` (for example 'orgin-response').
- `s3_website_cloudfront_tls_policy: TLSv1.1_2016` - AWS managed TLS version and cipher policy for Cloudfront. Check AWS [CloudFront docs](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/secure-connections-supported-viewer-protocols-ciphers.html) which are available.

For more details also check the `defaults/main.yml` file.

## Deploy of your website
To deploy your website you have to upload your websites code into the given bucket created by this role.
Use a deployment task in your repo for example. Also make sure to invalidate all cached files in CloudFront that where changed since the
last upload or use versioned filenames.

Example with AWS CLI:
`aws cloudfront create-invalidation --distribution-id XXXXX --invalidation-batch "Paths={Quantity=1,Items=['/index.html']},CallerReference=$(date)"`

## Dependencies
Depends on no other Ansible role.

## Example Playbook
Use the role in your existing playbook like this:

    - hosts: localhost
      vars:
        s3_website_bucket_name: 'my-fancy-frontend'
        s3_website_alias_domain_names:
          - 'my-fancy-frontend.com'
          - 'www.my-fancy-frontend.com'
        s3_website_certificate_arn: 'arn:aws:acm:us-east-1:1230000000000:certificate/64089f32-b35a-4cdb-x301-2bc982d4630x'
      roles:
         - mediapeers.s3-website-hosting

## License
BSD

## Author Information
Stefan Horning <horning@mediapeers.com>
