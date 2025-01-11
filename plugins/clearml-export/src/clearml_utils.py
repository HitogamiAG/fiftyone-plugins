from clearml.backend_api.session.client import APIClient
from clearml.backend_api.session import Session

import requests

def create_client(api_url, api_key, secret_key):
    session = Session(api_key=api_key, secret_key=secret_key, host=api_url)
    return APIClient(session=session)

def get_projects(api_url, api_key, secret_key):
    projects = requests.get(f'{api_url}projects.get_all',
                            auth=(api_key, secret_key)).json()['data']['projects']
    
    return projects

def get_datasets_by_project_id(api_url, api_key, secret_key, project_id):
    datasets = requests.get(f'{api_url}projects.get_all_ex', data={'id' : [project_id], 'include_stats' : True, 'search_hidden' : True},
                            auth=(api_key, secret_key)).json()['data']['projects'][-1]['sub_projects']
    
    datasets = [dataset for dataset in datasets if not dataset['name'].endswith('/.datasets')]
    return datasets

def get_versions_by_dataset_id(api_url, api_key, secret_key, dataset_id):
    versions = requests.post(f'{api_url}tasks.get_all_ex', data={"project":[dataset_id],
                                                                "system_tags":["dataset"],
                                                                "include_subprojects":False,
                                                                "search_hidden":True,
                                                                "only_fields":["id","runtime.version"]},
                            auth=(api_key, secret_key)).json()['data']['tasks']
    return versions

if __name__ == '__main__':
    import os

    projects = get_projects(os.getenv('FIFTYONE_CLEARML_API_URL'),
                            os.getenv('FIFTYONE_CLEARML_API_KEY'),
                            os.getenv('FIFTYONE_CLEARML_SECRET_KEY'))
    
    if not len(projects): raise Exception('No projects found')
    print(f"Random project id: {projects[-1]['id']}")
    
    datasets = get_datasets_by_project_id(os.getenv('FIFTYONE_CLEARML_API_URL'),
                                              os.getenv('FIFTYONE_CLEARML_API_KEY'),
                                              os.getenv('FIFTYONE_CLEARML_SECRET_KEY'), projects[-1]['id'])
    
    if not len(datasets): raise Exception('No datasets found')
    print(f'Random dataset id: {datasets[1]["id"]}')
    
    versions = get_versions_by_dataset_id(os.getenv('FIFTYONE_CLEARML_API_URL'),
                                          os.getenv('FIFTYONE_CLEARML_API_KEY'),
                                          os.getenv('FIFTYONE_CLEARML_SECRET_KEY'), datasets[1]['id'])
    
    print(versions)