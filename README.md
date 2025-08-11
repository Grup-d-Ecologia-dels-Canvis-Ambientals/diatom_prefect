# Diatom prefect

This project uses [Prefect](https://www.prefect.io/) to download and set up a series of image folders. It produces a directory structure specially adequate for image training:

```
data
└───downloads
│   |─ file1.zip
│   |─ file2.zip
│   |─ ...
└───results
    │─ train
        └─ class_folder_1
        └─ class_folder_2
        └─ class_folder_3
        ....
        └─ class_folder_n
    │─ test
        └─ class_folder_1
        └─ class_folder_2
        └─ class_folder_3
        ....
        └─ class_folder_n
```
Temptatively, once developed the workflow would implement these steps:  

1. Download and organize data, i.e. images, for training and testing.  
2. Create the docker image with the latest scripts for training and testing the model.  
3. Start a GPU-server (institutional computing services, cloud-based server, or local-server).  
3. Deploy the docker image in the server for training/testing the model.  
4. Run the train.py and test.py scripts.  
5. Download the trained model along with its evaluation results (if model trained some cloud service).  
6. Stop the GPU-server (important for not to incur in unnecessary costs).  
5. Deploy the model in the corresponding production models folder.  

## How to run this

### Clone this repository
git clone https://github.com/Grup-d-Ecologia-dels-Canvis-Ambientals/diatom_prefect.git  

### Create virtual environment

This project was created using python 3.12. To create a virtual environment, do this:
```
# create virtual env in folder called "venv"
python3 -m venv venv
# activate virtual env
source venv/bin/activate
# install packages
pip install -r requirements.txt
```

### Set up a prefect server

The best option to do this is to use the provided ```docker-compose.yml``` file. This file has default parameters for everything, including database users and passwords. **DO NOT RUN THIS IN PRODUCTION AS IS** if you intend to deploy this anywhere public, create an .env file and do variable substitution in the ```docker-compose.yml``` file.

To create and run the docker containers do:
```
docker compose up -d
```
To stop:
```
docker compose stop
```
The prefect server should be available at http://127.0.0.1:4200

### Create secrets

For the flow to run, you have to create on the server a JSON secret called "file-list".

This file contains the list of files to be downloaded. It is a json list of dictionaries. Each entry has the form:
```
{
    "file_url": "A public accessible url pointing to a *.zip file",
    "downloaded_file_name": "The name which will be given to the downloaded file, (i.e file_1.zip)",
    "exploded_folder_name": "The name of the folder contained in the zip file",
    "species_label":"Label of the species contained in the folder (i.e gomphonema_clavatum)"
}
```

### Run the task

To run the task, simply run the file 01_flow.py
```
python 01_flow.py
```

The task does the following:
- downloads the files in the file_list secret to data/downloads.
- explodes the files in the same data/downloads folder.
- moves the files to the results folder. It creates a train and test subfolders, and inside this folders creates one subfolder for each "species_label" in the file_list secret.
- It shuffles randomly the list of files for each downloaded folder, takes the first N_TEST files and puts them in data/results/test/[species_label]/, and the rest of files puts in data/results/train/[species_label]/
- It compresses the data folder to a file which has the name "diatom_set-YYYY-MM-DD-HH-mm-ss.zip"
- Finally it uploads the zip file to the local owncloud instance and deletes the local file.