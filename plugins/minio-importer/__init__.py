import os
from minio import Minio

import fiftyone as fo
import fiftyone.operators as foo
import fiftyone.operators.types as types
import fiftyone.types.dataset_types as fodt

class ImportFromMinio(foo.Operator):
    
    client = None
    
    @property
    def config(self):
        return foo.OperatorConfig(
            name="import_from_minio",
            label="Import from Minio",
            allow_delegated_execution=True,
            allow_immediate_execution=True,
            default_choice_to_delegated=True,
            dynamic=True,
        )
    
    def resolve_input(self, ctx):        
        if not self.client:
            self.client = create_client(
                ctx.secrets['FIFTYONE_MINIO_SERVER_ADDRESS'],
                ctx.secrets['FIFTYONE_MINIO_ACCESS_KEY'],
                ctx.secrets['FIFTYONE_MINIO_SECRET_KEY'],
                ctx.secrets.get('FIFTYONE_MINIO_SECURE', 'True'),
                ctx.secrets.get('FIFTYONE_MINIO_CERT_CHECK', 'True')
            )
            
        inputs = types.Object()
        
        is_minio_input_parsed = parse_minio_input(inputs, ctx, self.client)
        if is_minio_input_parsed:
            is_fiftyone_input_parsed = parse_fiftyone_input(inputs, ctx)
            if is_fiftyone_input_parsed:
                show_import_path_example(inputs, ctx, self.client)
        
        return types.Property(inputs, view = types.View(label="Import from Minio"))

    def execute(self, ctx):
        bucket = ctx.params.get('bucket')
        path_to_folder = ctx.params.get('path_to_folder')
        
        save_path_directory = ctx.params.get('directory')['absolute_path']
        save_path_folder_name = ctx.params.get('folder_name', None)
        
        if save_path_folder_name:
            extraction_path = os.path.join(save_path_directory, save_path_folder_name)
        else:
            extraction_path = save_path_directory
        
        found_objects = [obj for obj in self.client.list_objects(bucket, prefix=path_to_folder, recursive=True)]
        for obj in found_objects:
            minio_object_path = obj.object_name
            
            parts_to_trunc = len([part for part in path_to_folder.split('/') if part])
            minio_object_path_trunc = '/'.join(minio_object_path.split('/')[parts_to_trunc:])
            
            save_object_path = os.path.join(extraction_path, minio_object_path_trunc)
            
            if not os.path.exists(os.path.dirname(save_object_path)):
                os.makedirs(os.path.dirname(save_object_path))
            
            self.client.fget_object(bucket, minio_object_path, save_object_path)
        
        return {"status" : f"Imported {len(found_objects)}!"}

    def resolve_output(self, ctx):
        
        outputs = types.Object()
        outputs.str("status", label="Status", required=True)
        
        return types.Property(outputs, view = types.View(label="Dataset imported from Minio!"))

def register(p):
    p.register(ImportFromMinio)
    
def create_client(minio_host, minio_access_key, minio_secret_key, minio_secure, minio_cert_check):
    minio_secure = minio_secure == 'True'
    minio_cert_check = minio_cert_check == 'True' if minio_cert_check in ['True', 'False'] else minio_cert_check
    
    return Minio(
        endpoint=minio_host,
        access_key=minio_access_key,
        secret_key=minio_secret_key,
        secure=minio_secure,
        cert_check=minio_cert_check,
    )

def choose_bucket(inputs, ctx, client: Minio):
    bucket_choices = types.Choices()
    for bucket in client.list_buckets():
        bucket_choices.add_choice(bucket.name, label=bucket.name)
    
    inputs.enum("bucket", values=bucket_choices.values(), required=True, label = "Bucket: ", view=bucket_choices)

def choose_s3_path(inputs, ctx, client: Minio):
    inputs.str("path_to_folder", required=True, label = "Path to folder (like path/to/folder): ")
    
    if ctx.params.get('path_to_folder', None) is not None:
        found_objects = [obj for obj in client.list_objects(ctx.params.get('bucket'),
                                                            prefix=ctx.params.get('path_to_folder'),
                                                            recursive=True)]
        objects_count = len(found_objects)
        
        if objects_count > 0:
            found_files_info = types.Success(label=f"Found {objects_count} files recursively in the folder")
            prop_found_files_info = inputs.view('found_files_info', found_files_info)
            
            example_file = types.Success(label=f"Example file: {found_objects[0].object_name}")
            prop_example_file = inputs.view('example_file', example_file)
            
            return True
        else:
            no_files_warning = types.Warning(label="No files found in the folder")
            prop_no_files_warning = inputs.view('no_files_warning', no_files_warning)
            prop_no_files_warning.invalid = True
            return False
    else:
        no_path_warning = types.Warning(label="Please provide a path to a folder")
        prop_no_path_warning = inputs.view('no_path_warning', no_path_warning)
        prop_no_path_warning.invalid = True
        return False

def parse_minio_input(inputs, ctx, client):
    
    choose_bucket(inputs, ctx, client)
    if ctx.params.get('bucket', None) is not None:
        return choose_s3_path(inputs, ctx, client)

def parse_fiftyone_input(inputs, ctx):
    file_explorer = types.FileExplorerView(
        choose_dir=True,
        button_label="Choose a directory...",
    )
    inputs.file(
        "directory",
        required=True,
        label="Directory",
        description="Choose a directory of media to add to this dataset",
        view=file_explorer,
    )
    inputs.str(
        'folder_name',
        label='Folder name',
        description='Name of the folder to create in the directory or leave empty to extract in the root directory',
    )
    
    if ctx.params.get('directory', None) is not None:
        return True
    else:
        return False
    
def show_import_path_example(inputs, ctx, client: Minio):
    bucket = ctx.params.get('bucket')
    path_to_folder = ctx.params.get('path_to_folder')
    
    save_path_directory = ctx.params.get('directory')['absolute_path']
    save_path_folder_name = ctx.params.get('folder_name', None)
    
    if save_path_folder_name:
        extraction_path = os.path.join(save_path_directory, save_path_folder_name)
    else:
        extraction_path = save_path_directory
    
    minio_object = next(iter(client.list_objects(bucket, prefix=path_to_folder, recursive=True)))
    minio_object_path = minio_object.object_name
    
    parts_to_trunc = len([part for part in path_to_folder.split('/') if part])
    minio_object_path_trunc = '/'.join(minio_object_path.split('/')[parts_to_trunc:])
    
    final_example_save_path = os.path.join(extraction_path, minio_object_path_trunc)
    
    example_save_path = types.Success(label=f"Example save path: {final_example_save_path}")
    example_save_path_view = inputs.view('example_save_path_view', example_save_path)