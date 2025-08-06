from prefect import flow, task
import requests
from concurrent.futures import ThreadPoolExecutor
import zipfile
import os
import shutil
from pathlib import Path
import random
from prefect.blocks.system import Secret

BASE_DIR = "data"
DOWNLOADS_DIR = "downloads"
RESULTS_DIR = "results"
N_TEST = 10

@task(log_prints=True)
def download_file(url: str, output_file: str) -> bool:
    try:
        response = requests.get(url, stream=True, timeout=20)
        if response.status_code == 200:
            with open(output_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                print(f"Downloaded successfully as {output_file}")
                return True
        else:
            print(f"Failed to download. Status code: {response.status_code}")
            return False
    except Exception as e:
        print(f"Exception while downloading {url}: {e}")
        return False
    
@task(log_prints=True)
def create_directory_structure(files: list[dict]) -> dict:
    project_root = os.path.join(os.getcwd())
    print(f"Project root is {project_root}")
    try:
        print(f"Removing directory {BASE_DIR} ...")
        shutil.rmtree(BASE_DIR)
        print("Done!")
    except FileNotFoundError:
        print(f"Directory {BASE_DIR} does not exist, moving on...")
        pass

    downloads_dir = os.path.join(project_root,BASE_DIR, DOWNLOADS_DIR)
    results_dir = os.path.join(project_root,BASE_DIR, RESULTS_DIR)

    print(f"Creating directories")
    os.mkdir(BASE_DIR)    
    os.mkdir(os.path.join(BASE_DIR, DOWNLOADS_DIR))
    os.mkdir(os.path.join(BASE_DIR, RESULTS_DIR))

    species_folders = [ f['species_label'] for f in files ]

    for category in ['test','train']:
        os.mkdir( os.path.join(results_dir,category) )
        for species in species_folders:
            route = os.path.join(results_dir,category,species)
            os.mkdir( route )    
            print(f"Created directory { str(route) }")
    
    return {
        "project_root": project_root,
        "downloads_dir": downloads_dir,
        "results_dir": results_dir
    }

@task(log_prints=True)
def copy_files(files: list[dict]) -> None:
    download_and_output_folders = [ 
        ( os.path.join(BASE_DIR, DOWNLOADS_DIR,f['exploded_folder_name']), os.path.join(BASE_DIR, RESULTS_DIR), f['species_label']) for f in files
    ]    
    todo_list = []
    for download, output, species_label in download_and_output_folders:        
        base = Path(download)
        species_files = []
        for dirpath in base.rglob('*'):
            if dirpath.is_dir():
                species_files.extend([file for file in dirpath.glob('*.png')])
            else:
                species_files.append(dirpath)
        random.shuffle(species_files)
        files_test = species_files[:N_TEST+1]
        files_train = species_files[N_TEST+1:]
        todo_list.append({
            'files_train': files_train,
            'files_test': files_test,
            'output_dir_train': os.path.join(output,'train',species_label),
            'output_dir_test': os.path.join(output,'test',species_label),
        })    
    for item in todo_list:
        print(f"Copying files to {item['output_dir_train']} and {item['output_dir_test']}")
        files_test = item['files_test']
        files_train = item['files_train']
        for file in files_test:
            shutil.copy(file, item['output_dir_test'] )
        for file in files_train:
            shutil.copy(file, item['output_dir_train'] )
    
    
@task(log_prints=True)
def unzip_file(path_to_zip_file, directory_to_extract_to):
    print(f"Unzipping file {path_to_zip_file} to {directory_to_extract_to}")
    try:
        with zipfile.ZipFile(path_to_zip_file, 'r') as zip_ref:            
            zip_ref.extractall(directory_to_extract_to) 
            return True
    except Exception as e:
        print(f"Exception while unzipping {path_to_zip_file}: {e}")
        return False   

@task(log_prints=True)
def verify_all_downloads(results: list[bool]):
    if not all(results):
        raise Exception("One or more downloads failed.")
    print("All downloads successful!")

@task(log_prints=True)
def verify_all_unzips(results: list[bool]):
    if not all(results):
        raise Exception("One or more unzips failed.")
    print("All unzips successful!")

@flow(log_prints=True, retries=3)
def download_files_flow():   
    secret_block = Secret.load("file-list")
    files = secret_block.get()
    
    dirs = create_directory_structure(files)

    urls_and_zips = [ (f['file_url'],f['downloaded_file_name']) for f in files ]
    
    # Run download tasks concurrently using ThreadPoolExecutor
    with ThreadPoolExecutor() as executor:
        futures = []
        for url, output in urls_and_zips:
            futures.append(download_file.submit(url, os.path.join(dirs['downloads_dir'],output)))

    # Collect results
    results = [future.result() for future in futures]

    # Verify all succeeded
    verify_all_downloads(results)

    with ThreadPoolExecutor() as executor:
        futures = []
        for url, output in urls_and_zips:
            futures.append(unzip_file.submit( os.path.join(dirs['downloads_dir'],output), dirs['downloads_dir']))

    results = [future.result() for future in futures]

    verify_all_unzips(results)    

    copy_files(files)


if __name__ == "__main__":    
    download_files_flow()    