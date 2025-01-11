![alt text](assets/image.png)

Versionize data using Fiftyone and ClearML

## Installation

### 1. Download plugin

```shell
fiftyone plugins download \
    https://github.com/HitogamiAG/fiftyone-plugins \
    --plugin-names HitogamiAG/clearml-export
```

### 2. Install the requirements

```shell
fiftyone plugins requirements HitogamiAG/clearml-export --install
```

### 3. Set environemtn variables

See `.env_example`

### 4. Initialize ClearML on this machine

In CLI: `clearml-init` and follow instructions