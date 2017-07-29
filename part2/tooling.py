import os
import functools
import docker
import requests
import asyncio
from terminaltables import AsciiTable

# Reference: https://github.com/yodle/docker-registry-client/issues/42

AUTH_URL = 'https://auth.docker.io/token'
AUTH_SERVICE = 'registry.docker.io'
REG_URL = 'https://registry.hub.docker.com'
REG_HEADER_ACCEPT = 'application/vnd.docker.distribution.manifest.v2+json'
GET_MANIFESTS_V2_TEMPLATE = '{reg_url}/v2/{repo}/manifests/{ref}'

client = docker.from_env()

table = AsciiTable([['CONTAINER ID', 'TAG', 'UP TO DATE?']])
table.inner_column_border = table.inner_row_border\
    = table.inner_heading_row_border = table.outer_border = False

loop = asyncio.get_event_loop()

async def is_image_updated(repo, ref, sha):
    tag_url = {
        'reg_url': REG_URL,
        'repo': repo,
        'ref': ref,
    }
    querystring = {
        'service': AUTH_SERVICE,
        'scope': 'repository:%s:pull' % repo,
    }

    auth_response = await\
        loop.run_in_executor(None, functools.partial(requests.get, params=querystring), AUTH_URL)

    reg_headers = {
        'accept': REG_HEADER_ACCEPT,
        'Authorization': 'Bearer %s' % auth_response.json()['access_token']
    }

    get_manifests_v2_url = GET_MANIFESTS_V2_TEMPLATE.format(**tag_url)
    reg_response = await\
        loop.run_in_executor(None, functools.partial(requests.get, headers=reg_headers), get_manifests_v2_url)

    # print(reg_response.json()['config']['digest'])
    # print(reg_response.headers['docker-content-digest']) # this is the digest of the manifest
    return reg_response.json()['config']['digest'] == sha

async def append_and_refresh_output(repo, ref, awaitable_is_image_updated):
    table.table_data.append([repo, ref, str(await awaitable_is_image_updated).upper()])
    os.system('cls' if os.name == 'nt' else 'clear')
    print(table.table)

async def main():
    barrier = []

    for container in client.containers.list():
        image_ref = container.attrs['Config']['Image'].split(':')

        repo = image_ref[0]
        if '/' not in repo:
            repo = 'library/' + repo
        ref = image_ref[1] if len(image_ref) > 1 else 'latest'

        task_is_image_updated = loop.create_task(is_image_updated(repo, ref, container.attrs['Image']))
        barrier.append(append_and_refresh_output(container.short_id, ref, task_is_image_updated))

    await asyncio.wait(barrier)

loop.run_until_complete(main())
loop.close()
