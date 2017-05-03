#!/usr/bin/python
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.
DOCUMENTATION = '''
module: cloudfront
short_description: Create, delete and update actions for the main AWS
  Cloudfront actions.
description:
  - Read the AWS documentation for Cloudfront for the correct json values
      as there are too many to list here.
  - Creates distributions, streaming_distributions, invalidations,
      origin_access_ids
  - Deletes distributions, streaming_distributions, origin_access_ids
  - Updates distributions, streaming_distributions
version_added: "2.1"
requirements: [ boto3 ]
options:
  type:
    description:
      - specifies the resource to take action upon, streaming is
        streaming_distribution
    required: True
    choices: [
            'distribution',
            'origin_access_id',
            'invalidation',
            'streaming',
            ]
    default: None
  policy:
    description:
      - The path to the properly json formatted policy file or a
        properly formatted json policy as string, see
        https://github.com/ansible/ansible/issues/7005#issuecomment-42894813
        on how to use it properly
      - Used for creation and updating of resources
    required: false
    default: None
  resource_id:
    description:
      - Required when creating an invalidation against a distribution
      - Required for removal of distributions and origin_access_ids
    required: false
  state:
    description:
      - present to ensure resource is created or updated.
      - absent to remove resource
    required: false
    default: present
    choices: [ "present", "absent"]
  wait_for_deployed:
    description:
      - distributions and streaming_distributions need to be disabled
        before you can remove them.
      - Setting this to yes will allow this module to disable the
        distribution on your behalf, wait
      - until the status has changed to "Deployed" before removing your
        distribution. This has a timeout of 15 mins which is
        the recommended value from AWS.
      - this setting can also be used ensure a distribution,
        invalidation, origin_access_id is created or updated
    required: false
    choices: ['yes', 'no']
    default: no
author: Karen Cheng(@Etherdaemon)
extends_documentation_fragment: aws
'''

EXAMPLES = '''
# Simple example of creating a new distribution with a json file
- name: Create a new distribution
  cloudfront:
    type: distribution
    state: present
    policy: "{{ role_path }}/files/distribution.json"

- name: Create a new distribution and wait for deployed
  cloudfront:
    type: distribution
    state: present
    wait_for_deployed: yes
    policy: "{{ role_path }}/files/distribution.json"

- name: Create a new origin access identity
  cloudfront:
    type: origin_access_id
    state: present
    policy: "{{ role_path }}/files/origin_access.json"

#Disable and delete distribution
- name: Disable and wait for status to change to "Deployed" and delete
    distribution
  cloudfront:
    type: distribution
    state: absent
    resource_id: EEFF123DDFF
    wait_for_deployed: yes

- name: Create a new invalidation using policy template
  cloudfront:
    type: invalidation
    resource_id: EEFF123DDFF
    state: present
    policy: " {{ lookup( 'template', 'invalidation.json.j2') }} "
'''

RETURN = '''
result:
  description: The result of the create, delete or update action.
  returned: success
  type: dictionary or a list of dictionaries
'''

try:
    import json
    import botocore
    import boto3
    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False

import time


def date_handler(obj):
    return obj.isoformat() if hasattr(obj, 'isoformat') else obj


def get_existing_distributions(client, module):
    distributions = client.list_distributions()
    dist_configs = []
    if 'Items' in distributions['DistributionList']:
        for dist in distributions['DistributionList']['Items']:
            temp_object = dict()
            config = client.get_distribution_config(
                Id=dist['Id'])
            temp_object['Config'] = config['DistributionConfig']
            temp_object['ETag'] = config['ETag']
            temp_object['Id'] = dist['Id']
            temp_object['DomainName'] = dist['DomainName']
            dist_configs.append(temp_object)
    return dist_configs


def get_existing_origin_access_id(client, module):
    origin_access_ids = client.list_cloud_front_origin_access_identities()
    origin_access_configs = []
    if 'Items' in origin_access_ids['CloudFrontOriginAccessIdentityList']:
        for origin in origin_access_ids['CloudFrontOriginAccessIdentityList']['Items']:
            temp_object = dict()
            config = client.get_cloud_front_origin_access_identity_config(
                Id=origin['Id'])
            temp_object['Config'] = config['CloudFrontOriginAccessIdentityConfig']
            temp_object['ETag'] = config['ETag']
            temp_object['Id'] = origin['Id']
            origin_access_configs.append(temp_object)
    return origin_access_configs


def get_existing_invalidations(client, module):
    distribution_id = module.params.get('resource_id')
    if not distribution_id:
        module.fail_json(msg="distribution_id is required for invalidations")

    invalidations = client.list_invalidations(DistributionId=distribution_id)

    invalidation_configs = []
    if 'Items' in invalidations['InvalidationList']:
        for invalidation in invalidations['InvalidationList']['Items']:
            temp_object = dict()
            config = client.get_invalidation(
                DistributionId=distribution_id, Id=invalidation['Id'])
            temp_object['Config'] = config['Invalidation']['InvalidationBatch']
            temp_object['ETag'] = ""
            temp_object['Id'] = invalidation['Id']
            invalidation_configs.append(temp_object)
    return invalidation_configs


def get_existing_streaming_distributions(client, module):
    distributions = client.list_streaming_distributions()
    dist_configs = []
    for dist in distributions['StreamingDistributionList']['Items']:
        temp_object = dict()
        config = client.get_streaming_distribution_config(
            Id=dist['Id'])
        temp_object['Config'] = config['StreamingDistributionConfig']
        temp_object['ETag'] = config['ETag']
        temp_object['Id'] = dist['Id']
        temp_object['DomainName'] = dist['DomainName']
        dist_configs.append(temp_object)
    return dist_configs


def creation_setup(client, module):
    policy = None
    changed = False

    if module.params.get('policy'):
        try:
            with open(module.params.get('policy')) as json_data:
                try:
                    policy = json.load(json_data)
                    json_data.close()
                except ValueError as e:
                    module.fail_json(msg=str(e))
        except (OSError, IOError) as e:
            try:
                policy = json.loads(module.params.get('policy'))
            except ValueError as e:
                module.fail_json(msg=str(e))
        except Exception as e:
            module.fail_json(msg=str(e))

    invocations = {
        'distribution': {
            'get_config_method': get_existing_distributions,
        },
        'origin_access_id': {
            'get_config_method': get_existing_origin_access_id,
        },
        'invalidation': {
            'get_config_method': get_existing_invalidations,
        },
        'streaming': {
            'get_config_method': get_existing_streaming_distributions
        }
    }

    if 'CallerReference' not in policy:
        module.fail_json(msg='CallerReference is required in your policy')
    else:
        caller_reference = policy['CallerReference']

    resource_type = invocations[module.params.get('type')]
    existing = resource_type['get_config_method'](client, module)
    caller_reference_exists = False
    for item in existing:
        if caller_reference == item['Config']['CallerReference']:
            caller_reference_exists = True
            if cmp(policy, item['Config']) == 0:
                temp_results = item
                results = return_resource_details(client, module, temp_results)
            elif module.params.get('type') == "invalidation":
                module.fail_json(msg="AWS does not support updating"
                                    " invalidation configs, please"
                                    " create a new invalidation"
                                    " with your new config and"
                                    " use a new caller reference id instead")
            else:
                changed, results = update(client, module, policy, item['Id'], item['ETag'])

    if not caller_reference_exists:
        changed, results = creation(client, module, policy)

    return changed, results


def return_resource_details(client, module, temp_results):
    params = dict()

    invocations = {
        'distribution': {
            'get_resource_details': client.get_distribution,
        },
        'origin_access_id': {
            'get_resource_details': client.get_cloud_front_origin_access_identity,
        },
        'invalidation': {
            'get_resource_details': client.get_invalidation,
        },
        'streaming': {
            'get_resource_details': client.get_streaming_distribution
        }
    }

    if module.params.get('type') == "invalidation":
        params['DistributionId'] = module.params.get('resource_id')

    params['Id'] = temp_results['Id']
    resource_type = invocations[module.params.get('type')]
    resource_details = json.loads(json.dumps(resource_type['get_resource_details'](**params), default=date_handler))

    return resource_details


def creation(client, module, policy):
    changed = False
    params = dict()
    args = dict()

    invocations = {
        'distribution': {
            'method': client.create_distribution,
            'config_param': "DistributionConfig",
            'result_key': "Distribution",
        },
        'origin_access_id': {
            'method': client.create_cloud_front_origin_access_identity,
            'config_param': "CloudFrontOriginAccessIdentityConfig",
            'result_key': "CloudFrontOriginAccessIdentity",
        },
        'invalidation': {
            'method': client.create_invalidation,
            'config_param': "InvalidationBatch",
            'result_key': "Invalidation",
        },
        'streaming': {
            'method': client.create_streaming_distribution,
            'config_param': "StreamingDistributionConfig",
            'result_key': "StreamingDistribution",
        },
    }
    resource_type = invocations[module.params.get('type')]
    params[resource_type['config_param']] = policy
    if module.params.get('type') == "invalidation":
        params['DistributionId'] = module.params.get('resource_id')
        args['DistributionId'] = module.params.get('resource_id')

    invocation = resource_type['method']
    result = json.loads(json.dumps(invocation(**params), default=date_handler))

    if module.params.get('wait_for_deployed'):
        args['Id'] = result[resource_type['result_key']]['Id']
        status_achieved = wait_for_deployed_status(client, module, **args)
        if not status_achieved:
            module.fail_json(msg="Timed out waiting for the resource to finish"
                                " deploying, please check the AWS console for"
                                " the latest status.")

    changed = True
    return (changed, result)


def update(client, module, policy, resource_id, etag):
    changed = False
    params = dict()
    invocations = {
        'distribution': {
            'method': client.update_distribution,
            'config_param': "DistributionConfig"
            },
        'origin_access_id': {
            'method': client.update_cloud_front_origin_access_identity,
            'config_param': "CloudFrontOriginAccessIdentityConfig"
            },
        'streaming': {
            'method': client.create_streaming_distribution,
            'config_param': "StreamingDistributionConfig",
            },
    }

    params[invocations[module.params.get('type')]['config_param']] = policy
    params['Id'] = resource_id
    params['IfMatch'] = etag

    invocation = invocations[module.params.get('type')]['method']
    result = json.loads(json.dumps(invocation(**params), default=date_handler))
    if module.params.get('wait_for_deployed'):
        args = dict()
        args['Id'] = params['Id']
        status_achieved = wait_for_deployed_status(client, module, **args)
        if not status_achieved:
            module.fail_json(msg="Timed out waiting for the resource to finish"
                                " deploying, please check the AWS console for"
                                " the latest status.")

    changed = True
    return (changed, result)


def disable_distribution(client, module):
    params = dict()

    invocations = {
        'distribution': {
            'method': client.get_distribution,
            'config_param': "DistributionConfig",
            'dist_key': 'Distribution',
        },
        'streaming': {
            'method': client.get_streaming_distribution,
            'config_param': "StreamingDistributionConfig",
            'dist_key': 'StreamingDistribution',
        },
    }
    resource_type = invocations[module.params.get('type')]
    resource_id = module.params.get('resource_id')
    params['Id'] = resource_id
    get_result = resource_type['method'](**params)

    if get_result[resource_type['dist_key']][resource_type['config_param']]['Enabled']:
        new_policy = get_result[resource_type['dist_key']][resource_type['config_param']]
        new_policy['Enabled'] = False
        update(client, module, new_policy, resource_id, get_result['ETag'])

    status_achieved = wait_for_deployed_status(client, module, **params)

    if not status_achieved:
        module.fail_json(msg="Timed out disabling the resource, please try again")
    else:
        updated_result = client.get_distribution_config(**params)
        return status_achieved, updated_result


def wait_for_deployed_status(client, module, max_retries=30, **args):
    polling_increment_secs = 30
    status_achieved = False
    invocations = {
        'distribution': {
            'method': client.get_distribution,
            'result_key': 'Distribution',
        },
        'origin_access_id': {
            'method': client.get_cloud_front_origin_access_identity,
            'result_key': "CloudFrontOriginAccessIdentity"
        },
        'invalidation': {
            'method': client.get_invalidation,
            'result_key': "Invalidation"
        },
        'streaming': {
            'method': client.get_streaming_distribution,
            'result_key': 'StreamingDistribution',
        },
    }
    resource_type = invocations[module.params.get('type')]

    for x in range(0, max_retries):
        result = resource_type['method'](**args)[resource_type['result_key']]
        current_status = result['Status']
        if current_status == 'Deployed' or current_status == 'Completed':
            status_achieved = True
            break
        time.sleep(polling_increment_secs)

    return status_achieved


def removal_setup(client, module):
    changed = False
    params = dict()

    invocations = {
        'distribution': {
            'method': client.get_distribution_config,
            'config_param': "DistributionConfig"
            },
        'origin_access_id': {
            'method': client.get_cloud_front_origin_access_identity_config,
            'config_param': "CloudFrontOriginAccessIdentityConfig",
            },
        'streaming': {
            'method': client.get_streaming_distribution_config,
            'config_param': "StreamingDistributionConfig",
            },
    }

    if module.params.get('type') == "invalidation":
        module.fail_json(msg="Invalidations cannot be updated or removed")
    elif not module.params.get('resource_id'):
        module.fail_json(msg="resource_id is requried for removing a resource")
    elif module.params.get('wait_for_deployed'):
        status_achieved, config = disable_distribution(client, module)
    else:
        invocation = invocations[module.params.get('type')]['method']
        config = invocation(Id=module.params.get('resource_id'))

    if not config[invocations[module.params.get('type')]['config_param']]['Enabled']:
        resource_id = module.params.get('resource_id')
        etag = config['ETag']
        changed, result = removal(client, module, resource_id, etag)
    else:
        module.fail_json(msg="Resource must be disabled before you can remove it from AWS")

    return changed, result


def removal(client, module, resource_id, etag):
    changed = False
    params = dict()

    invocations = {
        'distribution': client.delete_distribution,
        'origin_access_id': client.delete_cloud_front_origin_access_identity,
        'streaming': client.delete_streaming_distribution
    }

    params['Id'] = resource_id
    params['IfMatch'] = etag

    invocation = invocations[module.params.get('type')]
    result = json.loads(json.dumps(invocation(**params), default=date_handler))
    changed = True
    return (changed, result)


def main():
    argument_spec = ec2_argument_spec()
    argument_spec.update(dict(
        type=dict(choices=[
            'distribution',
            'origin_access_id',
            'invalidation',
            'streaming',
        ], required=True),
        policy=dict(),
        resource_id=dict(),
        state=dict(default='present', choices=['present', 'absent']),
        wait_for_deployed=dict(type='bool', default=False),
        )
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
    )

    # Validate Requirements
    if not HAS_BOTO3:
        module.fail_json(msg='json and botocore/boto3 is required.')

    state = module.params.get('state').lower()
    #Cloudfront is non-region specific - default global region to us-east-1/US Standard
    module.params['region'] = 'us-east-1'

    try:
        region, ec2_url, aws_connect_kwargs = get_aws_connection_info(module, boto3=True)
        cloudfront = boto3_conn(module, conn_type='client', resource='cloudfront', region=region, endpoint=ec2_url, **aws_connect_kwargs)
    except Exception as e:
        module.fail_json(msg="Can't authorize connection - "+str(e))

    #Ensure resource is present
    if state == 'present':
        (changed, results) = creation_setup(cloudfront, module)
    else:
        (changed, results) = removal_setup(cloudfront, module)

    module.exit_json(changed=changed, result=results)


# import module snippets
from ansible.module_utils.basic import *
from ansible.module_utils.ec2 import *

if __name__ == '__main__':
    main()
