import os
import base64
import zipfile
import io

import fiftyone as fo
import fiftyone.operators as foo
import fiftyone.operators.types as types

class ZipExtractor(foo.Operator):
    @property
    def config(self):
        return foo.OperatorConfig(
            name="extract_zip",
            label="Upload .zip files and extract on filesystem",
            allow_delegated_execution=True,
            allow_immediate_execution=True,
            default_choice_to_delegated=True,
            dynamic=True,
        )
    
    def resolve_input(self, ctx):
        inputs = types.Object()
        
        inputs.obj(
            "zip_file",
            required=True,
            label="Zip file",
            description="Choose a .zip file to extract on host machine",
            view=types.FileView(label="Zip file")
        )
        ready = bool(ctx.params.get("zip_file", None))
        
        if ready:
        
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
        
        return types.Property(inputs, view = types.View(label="Import a zip file"))
        
    def execute(self, ctx):
        
        zip_fileobj = ctx.params['zip_file']
        content = base64.b64decode(zip_fileobj["content"])
        
        directory = ctx.params['directory']
        folder_name = ctx.params.get('folder_name', None)
        
        if folder_name:
            extraction_path = os.path.join(directory['absolute_path'], folder_name)
        else:
            extraction_path = directory['absolute_path']
            
        if not os.path.exists(extraction_path):
            os.makedirs(extraction_path)
        
        extract_zip_file(content, extraction_path)
        
        return {'message' : f'Zip content extracted in {extraction_path}'}
        
    def resolve_output(self, ctx):
        outputs = types.Object()
        outputs.str('message', label='Message', required=True)
        
        return types.Property(outputs, view = types.View(label="Dataset uploaded!"))
    
def register(p):
    p.register(ZipExtractor)
    
def extract_zip_file(content, directory):
    with zipfile.ZipFile(io.BytesIO(content)) as zip_ref:
        zip_ref.extractall(directory)