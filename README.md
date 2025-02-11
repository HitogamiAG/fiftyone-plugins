![alt text](assets/image.png)

Collection of plugins to integrate FiftyOne and ClearML

| Plugin | Name | Desc | Has additional requirements |
| - | - | - | - |
| Clearml Export | clearml-export | Export from FiftyOne and create new datasets and dataset versions in ClearML | + |
| Dataset Splitter | dataset-splitter | Attach split tags (e.g. train,val) to images based on image hash. Tags can be used during export to ClearML (currently only YOLOv5 dataset format) | |
| Zip extractor | zip-extractor | Extract images from zip to host machine to import images in FiftyOne (currently with poor optimization) | |
| Minio importer | minio-importer | Import files from Minio | + |

## Plugin installation

### 1. Download plugin

```shell
fiftyone plugins download \
    https://github.com/HitogamiAG/fiftyone-plugins \
    --plugin-names HitogamiAG/clearml-export
```

### 2. Install the additional requirements

```shell
fiftyone plugins requirements HitogamiAG/clearml-export --install
```

### 3. Set environemnt variables

See `.env_example`

### 4. Initialize ClearML on this machine

In CLI: `clearml-init` and follow instructions

## Development

### 1. Clone repository

```shell
git clone https://github.com/HitogamiAG/fiftyone-plugins && cd fiftyone-plugins
```

### 2. Create venv and install dependencies

```shell
python -m venv .venv && source .venv/bin/activate && pip install fiftyone clearml minio
```

### 3. Set environemnt variables

See `.env_example`

### 4. Set FIFTYONE_PLUGINS_DIR to `plugins` folder in repo

```shell
export FIFTYONE_PLUGINS_DIR=$(pwd)/plugins
```

### 5. Run FiftyOne

```shell
python tests/fiftyone_local.py
```

There is no need to restart FiftyOne to apply changes in plugins' source code. Just call plugin function again.