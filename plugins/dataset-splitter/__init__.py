import hashlib

import fiftyone as fo
import fiftyone.operators as foo
import fiftyone.operators.types as types

class DatasetSplitter(foo.Operator):
    @property
    def config(self):
        return foo.OperatorConfig(
            name="split_by_hash",
            label="Split dataset into sets by image hash",
            allow_delegated_execution=True,
            allow_immediate_execution=True,
            default_choice_to_delegated=True,
            dynamic=True,
        )
    
    def resolve_input(self, ctx):
        inputs = types.Object()
        
        if ctx.dataset is None:
            warning = types.Warning(label="No dataset found in context. Please load a dataset.")
            prop = inputs.view("warning", warning)
            prop.invalid = True
            return types.Property(inputs, view = types.View(label="Simple dataset input example"))
        
        inputs.str("split_names", label="Split names (f.e. 'train,val,test')", required=True)
        inputs.str("split_ratios", label="Split ratios (f.e. '0.7,0.2,0.1')", required=True)
        
        if ctx.has_custom_view:
            inputs.bool("use_view", label="Apply only to current view", required=True)
        
        return types.Property(inputs, view = types.View(label="Simple dataset input example"))
    
    def execute(self, ctx):
        use_view = ctx.params.get('use_view', False)
        
        if use_view:
            dataset = ctx.dataset.view()
        else:
            dataset = ctx.dataset
        
        try:
            split_names = ctx.params['split_names'].split(',')
            split_probs = [float(x) for x in ctx.params['split_ratios'].split(',')]
            
            split_probs = [split_prob / sum(split_probs) for split_prob in split_probs]
            
            if len(split_names) != len(split_probs):
                raise ValueError("Number of split names and split ratios should match. Num names: %d, num ratios: %d" % (len(split_names), len(split_probs)))
            
        except Exception as e:
            raise ValueError(f"Error parsing split names and ratios: {e}")
        
        split_counter = {split_name: 0 for split_name in split_names}
        for sample in dataset:
            sample_hash = compute_hash(sample.filepath)
            split_name = get_split_by_hash(sample_hash, split_names, split_probs.copy())
            
            if split_name not in sample.tags:
                sample.tags.append(split_name)
            
            split_counter[split_name] += 1
            
            sample.save()
        
        return {"split_counts" : str(split_counter)}

    def resolve_output(self, ctx):
        outputs = types.Object()
        outputs.str(
            'split_counts',
            label='Split counts',
        )
        return types.Property(outputs, view = types.View(label="Dataset uploaded!"))

def register(p):
    p.register(DatasetSplitter)
   
def compute_hash(filepath):
    hasher = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

def get_split_by_hash(hash, splits, splits_probs):
    hash_int = int(hashlib.sha256(hash.encode()).hexdigest(), 16)
    rand_float = hash_int / (2**256)
    
    for i, split_prob in enumerate(splits_probs):
        if i > 0:
            splits_probs[i] = splits_probs[i-1] + split_prob
    
    for split_name, split_prob in zip(splits, splits_probs):
        if rand_float < split_prob:
            return split_name
    
    raise ValueError("Something went wrong in splits: sum(normed_probs) < 1")