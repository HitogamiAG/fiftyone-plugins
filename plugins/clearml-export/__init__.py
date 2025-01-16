import tempfile
from clearml import Dataset
import fiftyone as fo
import fiftyone.operators as foo
import fiftyone.operators.types as types
import fiftyone.types.dataset_types as fodt

from .src.clearml_utils import (create_client, get_projects, get_datasets_by_project_id, get_versions_by_dataset_id)

EXPORT_FORMATS = [
    fodt.ImageDirectory,
    fodt.FiftyOneImageClassificationDataset,
    fodt.ImageClassificationDirectoryTree,
    fodt.TFImageClassificationDataset,
    fodt.FiftyOneImageDetectionDataset,
    fodt.FiftyOneTemporalDetectionDataset,
    fodt.COCODetectionDataset,
    fodt.VOCDetectionDataset,
    fodt.YOLOv4Dataset,
    fodt.YOLOv5Dataset,
    fodt.TFObjectDetectionDataset,
    fodt.ImageSegmentationDirectory,
    fodt.CVATImageDataset,
    fodt.FiftyOneImageLabelsDataset,
    fodt.BDDDataset,
    fodt.FiftyOneDataset
]
EXPORT_FORMATS_DICT = {export_format.__name__ : export_format for export_format in EXPORT_FORMATS}

SUPPORT_SPLITS = [
    fodt.YOLOv5Dataset
]

class ExportToClearml(foo.Operator):
    
    client = None
    
    @property
    def config(self):
        return foo.OperatorConfig(
            name="export_to_clearml",
            label="Export to ClearML",
            allow_delegated_execution=True,
            allow_immediate_execution=True,
            default_choice_to_delegated=True,
            dynamic=True,
        )
    
    def resolve_input(self, ctx):        
        if not self.client:
            self.client = create_client(
                ctx.secrets['FIFTYONE_CLEARML_API_URL'],
                ctx.secrets['FIFTYONE_CLEARML_API_KEY'],
                ctx.secrets['FIFTYONE_CLEARML_SECRET_KEY']
            )
            
        inputs = types.Object()
        
        if ctx.dataset is None:
            warning = types.Warning(label="No dataset found in context. Please load a dataset.")
            prop = inputs.view("warning", warning)
            prop.invalid = True
            return types.Property(inputs, view = types.View(label="Simple dataset input example"))
        
        is_fiftyone_inputs_parsed = parse_fiftyone_inputs(inputs, ctx)
        
        if is_fiftyone_inputs_parsed:
            parse_clearml_inputs(inputs, ctx)
        
        return types.Property(inputs, view = types.View(label="Simple dataset input example"))

    def execute(self, ctx):
        
        with tempfile.TemporaryDirectory() as temp_dir:
            #--- Export to filesystem
            dataset = ctx.dataset
            label_field = ctx.params['label_field']
            export_format = EXPORT_FORMATS_DICT[ctx.params['export_format']]
            export_splits = ctx.params.get('export_splits', None)
            
            if ctx.params.get("use_view", False):
                dataset = ctx.view
            
            if export_splits is None:
                dataset.export(
                    export_dir=temp_dir,
                    dataset_type=export_format,
                    label_field=label_field)
            else:
                classes = get_classes(dataset, label_field)
                export_splits = export_splits.split(',')
                
                for export_split in export_splits:
                    split_view = dataset.match_tags(export_split)
                    split_view.export(
                        export_dir=temp_dir,
                        dataset_type=export_format,
                        label_field=label_field,
                        split=export_split,
                        classes = classes)
                
            #--- Upload to ClearML
            dataset_name = ctx.params['dataset_name']
            dataset_project = ctx.params['project_name']
            parent_version_id = [] if ctx.params['parent_version_id'] is None else [ctx.params['parent_version_id']]
            dataset_version_name = ctx.params['dataset_version_name']
            
            dataset = Dataset.create(
                dataset_name=dataset_name,
                dataset_project=dataset_project,
                parent_datasets=parent_version_id,
                dataset_version=dataset_version_name,
                description='Exported from FiftyOne',
            )
            
            dataset.add_files(path=temp_dir)
            dataset.upload()
            dataset.finalize()
            
            return {"status" : "Dataset uploaded!"}

    def resolve_output(self, ctx):
        outputs = types.Object()
        return types.Property(outputs, view = types.View(label="Dataset uploaded!"))

def register(p):
    p.register(ExportToClearml)
    
def choose_project_source(inputs, ctx):
    project_actions = types.Choices()
    project_actions.add_choice("create", label="Create project")
    project_actions.add_choice("use", label="Use existing project")
    
    inputs.enum("project_action", values=project_actions.values(), required=True, label = "Project source: ", view=project_actions)
    
    return ctx.params.get('project_action', None)

def choose_project(inputs, ctx):
    projects = get_projects(ctx.secrets['FIFTYONE_CLEARML_API_URL'],
                            ctx.secrets['FIFTYONE_CLEARML_API_KEY'],
                            ctx.secrets['FIFTYONE_CLEARML_SECRET_KEY'])
    project_choices = types.AutocompleteView(space=6)
    for project in projects:
        project_choices.add_choice(project['id'], label=project['name'])
    inputs.enum("project_id", values=project_choices.values(), required=True, label="Project ID", view=project_choices)
    
    return ctx.params.get('project_id', None), {project['id'] : project['name'] for project in projects}

def choose_dataset_source(inputs, ctx):
    dataset_actions = types.Choices()
    dataset_actions.add_choice("create", label="Create dataset")
    dataset_actions.add_choice("use", label="Use existing dataset")
    
    inputs.enum("dataset_action", values=dataset_actions.values(), required=True, label = "Dataset source: ", view=dataset_actions)
    
    return ctx.params.get('dataset_action', None)

def choose_dataset(inputs, ctx):
    datasets = get_datasets_by_project_id(ctx.secrets['FIFTYONE_CLEARML_API_URL'],
                                          ctx.secrets['FIFTYONE_CLEARML_API_KEY'],
                                          ctx.secrets['FIFTYONE_CLEARML_SECRET_KEY'],
                                          ctx.params['project_id'])
    datasets = [dataset for dataset in datasets if not dataset['name'].endswith('/.datasets')]
    for dataset in datasets:
        dataset['name'] = dataset['name'].split('/')[-1]
    
    dataset_choices = types.AutocompleteView(space=6)
    for dataset in datasets:
        dataset_choices.add_choice(dataset['id'], label=dataset['name'])
    inputs.enum("dataset_id", values=dataset_choices.values(), required=True, label="Dataset name:", view=dataset_choices)
    
    return ctx.params.get('dataset_id', None), {dataset['id'] : dataset['name'] for dataset in datasets}

def choose_dataset_version(inputs, ctx):
    versions = get_versions_by_dataset_id(ctx.secrets['FIFTYONE_CLEARML_API_URL'],
                                        ctx.secrets['FIFTYONE_CLEARML_API_KEY'],
                                        ctx.secrets['FIFTYONE_CLEARML_SECRET_KEY'],
                                        ctx.params['dataset_id'])
    
    version_choices = types.AutocompleteView(space=6)
    for version in versions:
        version_choices.add_choice(version['id'], label=version['runtime']['version'])
    inputs.enum("version_id", values=version_choices.values(), label="Parent version name (choose or leave empty): ", view=version_choices)
    
    return ctx.params.get('version_id', None)

def parse_clearml_inputs(inputs, ctx):
    project_name = None
    dataset_name = None
    dataset_version_name = None
    parent_version_id = None
    
    chosen_project_action = choose_project_source(inputs, ctx)
    if chosen_project_action == "use":
        chosen_project_id, projects_id_name_mapping = choose_project(inputs, ctx)
        project_name = projects_id_name_mapping.get(chosen_project_id, None)
        
        if chosen_project_id is not None:
            chosen_dataset_action = choose_dataset_source(inputs, ctx)
            
            if chosen_dataset_action == "use":
                chosen_dataset_id, datasets_id_name_mapping = choose_dataset(inputs, ctx)
                dataset_name = datasets_id_name_mapping.get(chosen_dataset_id, None)
                
                if chosen_dataset_id is not None:
                    parent_version_id = choose_dataset_version(inputs, ctx)
                    
                    inputs.str("dataset_version", label="Name of new dataset version:", required=True)
                    
            elif chosen_dataset_action == "create":
                inputs.str("dataset_name", label="Name of new dataset:", required=True)
                inputs.str("dataset_version", label="Name of new dataset version:", required=True)
                
                dataset_name = ctx.params.get("dataset_name", None)
                dataset_version_name = ctx.params.get("dataset_version", None)
                
    elif chosen_project_action == "create":
        inputs.str("project_name", label="Name of new project: ", required=True)
        inputs.str("dataset_name", label="Name of new dataset: ", required=True)
        inputs.str("dataset_version", label="Name of new dataset version: ", required=True)
        
        project_name = ctx.params.get("project_name", None)
        dataset_name = ctx.params.get("dataset_name", None)
        dataset_version_name = ctx.params.get("dataset_version", None)
    
    ctx.params['project_name'] = project_name
    ctx.params['dataset_name'] = dataset_name
    ctx.params['dataset_version_name'] = dataset_version_name
    ctx.params['parent_version_id'] = parent_version_id
    
    return all([project_name is not None, dataset_name is not None, dataset_version_name is not None])

def choose_label_fields(inputs, ctx):
    if ctx.has_custom_view and ctx.params.get("use_view", False):
        label_fields = ctx.view._get_label_fields()
    else:
        label_fields = ctx.dataset._get_label_fields()
        
    label_choices = types.Choices()
    for field in label_fields:
        label_choices.add_choice(field, label=field)
    
    inputs.enum("label_field", values=label_choices.values(), required=True, label="Label field to export", view=label_choices)
    
    return ctx.params.get("label_field", None)

def choose_export_format(inputs, ctx):
    export_format_choices = types.Choices()
    
    for export_format in EXPORT_FORMATS_DICT.keys():
        export_format_choices.add_choice(export_format, label=export_format)
    
    inputs.enum("export_format", values=export_format_choices.values(), required=True, label="Export format", view=export_format_choices)
    
    return ctx.params.get("export_format", None)

def choose_splits_to_export(inputs, ctx):
    inputs.str("export_splits", label="Splits to export (f.e. 'train,val,test') (default: 'val'): ")
    export_splits = ctx.params.get("splits", None)
    
    return export_splits

def get_classes(dataset, label_field):
    classes = set()
    for sample in dataset:
        for instance in sample[label_field].to_dict().values()[1]:
            classes.update(instance.to_dict()['label'])
    
    return list(classes)

def parse_fiftyone_inputs(inputs, ctx):
    
    if ctx.has_custom_view:
        inputs.bool("use_view", label="Export only current view", required=True)
    
    label_field = choose_label_fields(inputs, ctx)
    
    if label_field is not None:
        export_format = choose_export_format(inputs, ctx)
        
        if export_format is not None and EXPORT_FORMATS_DICT[export_format] in SUPPORT_SPLITS:
            export_splits = choose_splits_to_export(inputs, ctx)
        else:
            export_splits = None
        
    else:
        export_format = None
        
    return all([label_field is not None, export_format is not None])