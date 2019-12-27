import sys
import os
import json
import time
from datetime import datetime
import logging
import csv
import requests
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

from lxml import etree, html

logging.basicConfig(filename="test.log")

#Creating an object 
logger=logging.getLogger()
#Setting the threshold of logger to DEBUG 
logger.setLevel(logging.INFO)

now = datetime.now()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DOMAIN = "https://partstore.agriculture.newholland.com"
BASE_URL = "%s/us/json.php" % DOMAIN
MODEL_FACE_URL = "%s?target=epc_b2c_gateway&locale=en&method=getModelFacetValues" % BASE_URL
SEARCH_URL = "%s/us/parts-search.html" % DOMAIN
MODEL_PAGE_URL = "%s/us/parts-search.html#epc::mr" % DOMAIN
ASSEMBLY_LIST_URL = "%s/us/json.php?target=epc_b2c_gateway" % DOMAIN
ASSEMBLY_ASSETS_URL = '%s/us/json.php?target=epc_b2c_gateway&locale=en&method=getAssemblyRevisionDetail&assembly_revision_id=' % DOMAIN

DEFAULT_FIELD = 'New Holland Agriculture'
CSV_HEADERS = ['field', 'product_type', 'product_line', 'serie', 'model',
                'model_id', 'product_id', 'product_name', 'folder_id', 'image',
                'folder_name', 'part_name', 'description', 'sku', 'quantity', 'is_scraped']

def post_api(url, payload):
    try:
        r = requests.post(MODEL_FACE_URL, data=payload)
        return r.json()
    except Exception as e:
        raise Exception(e)

def get_api(url):
    try:
        r = requests.get(url)
        return r.json()
    except Exception as e:
        raise Exception(e)


def log(msg):
    current_time = now.strftime("%Y-%m-%d %H:%M:%S")
    logging.info("{} at {}.\n".format(msg, current_time))

if __name__ == "__main__":
    results = []
    existings = []
    number_of_results = 0
    ext_models = []
    output_path = "{}/output".format(BASE_DIR)
    is_all = False

    if not os.path.exists(output_path):
        os.makedirs(output_path)

    csv_path = output_path+"/output.csv"
    if not os.path.exists(csv_path):
        # with open(csv_path, mode='w', newline='') as csv_file:
        with open(csv_path, mode='w') as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=CSV_HEADERS)
            writer.writeheader()

    run_type = "model"
    if sys.argv[1] == "output":
        run_type = "output"

    with open(csv_path) as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            existings.append(row)
            if 'model_id' in row and row['model_id'] not in ext_models:
                ext_models.append(row['model_id'])

    if run_type == "model":
        print("Model Done!")
        sys.exit(0)
        # with open(output_path+'/models.csv', mode='w', newline='') as csv_file:
        with open(output_path+'/models.csv', mode='w') as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=CSV_HEADERS)
            writer.writeheader()

            try:
                payload = { 'facets[]': 'type_s'}
                product_types = post_api(MODEL_FACE_URL, payload)

                if product_types and len(product_types) > 0:
                    for ptype in product_types[0]['facetValues']:
                        item = dict()

                        product_lines = post_api(MODEL_FACE_URL, {
                            'selectedValues[type_s]': ptype, 'facets[]': 'sub_type_s' })

                        if product_lines and len(product_lines) > 0:
                            for pline in product_lines[0]['facetValues']:
                                series = post_api(MODEL_FACE_URL, {
                                    'selectedValues[type_s]': ptype,
                                    'selectedValues[sub_type_s]': pline,
                                    'facets[]': 'model_line_s'
                                })

                                if series and len(series) > 0:
                                    for pserie in series[0]['facetValues']:
                                        models = post_api(MODEL_FACE_URL, {
                                            'start': 0,
                                            'selectedValues[type_s]': ptype,
                                            'selectedValues[sub_type_s]': pline,
                                            'selectedValues[model_line_s]': pserie,
                                            'method': 'getAllModel',
                                            'limit': 30,
                                            'field_list': [
                                                {"name":"product_name_s"},
                                                {"name":"product_id"},
                                                {"name":"code"}
                                            ],
                                            'fields': None,
                                            'facets[]': 'model_line_s'
                                        })

                                        if models and 'numFound' in models and models['numFound'] > 0:
                                            for pmodel in models['docs']:
                                                item = {
                                                    'field': DEFAULT_FIELD,
                                                    'product_type': ptype,
                                                    'product_line': pline,
                                                    'serie': pserie,
                                                    'model_id': pmodel['model_id'],
                                                    'product_id': pmodel['product_id'],
                                                    'product_name': pmodel['product_name'],
                                                    'is_scraped': 0
                                                }

                                                if pmodel['model_id'] in ext_models:
                                                    item['is_scraped'] = 1

                                                number_of_results = number_of_results + 1
                                                results.append(item)
                                                writer.writerow(item)
            except Exception as e:
                print("Model Error!")
                log("** line: 140 **: ")
                log(e)

        print("Model Done!")

    if run_type == "output":
        # if sys.argv[2] == "new":
        #     is_all = True
        with open(output_path+'/filter_models.csv') as csv_file:
            reader = csv.DictReader(csv_file)
            for row in reader:
                if int(row['is_scraped']) == 1:
                    results.append(row)

        # with open(output_path+'/filter_models.csv') as csv_file:
        #     reader = csv.DictReader(csv_file)
        #     ext_models = []
        #     for row in reader:
        #         if row['model_id'] not in ext_models:
        #             ext_models.append(row)

        # with open(output_path+'/output.csv', mode='a', newline='') as csv_file:
        with open(output_path+'/output.csv', mode='w') as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=CSV_HEADERS)
            writer.writeheader()

            driver = webdriver.Chrome(executable_path=BASE_DIR+"/chromedriver.exe")
            driver.set_window_size(1850, 1000)
            try:
                # section to scrape assemblies of the model
                log("number of results: " + str(len(results)))
                for entry in results:
                    # if  is_all == False and entry['model_id'] in ext_models:
                    #     pass
                    # else:
                    driver.get(MODEL_PAGE_URL+entry['model_id'])
                    wait = WebDriverWait(driver, 15)
                    men_menu = wait.until(EC.visibility_of_element_located((By.XPATH, '//ul[@class="x-tree-node-ct"]//li[@class="x-tree-node"]')))

                    source = driver.page_source.encode("utf8")
                    tree = etree.HTML(source)
                    
                    folders = tree.xpath('//ul[@class="x-tree-node-ct"]//li[@class="x-tree-node"]//div')
                    log("** line: 183 **: number of folders:" + str(len(folders)))
                    for folder in folders:
                        try:
                            folder_id = folder.attrib['ext:tree-node-id']
                            folder_name = folder.xpath('.//a//span//text()')[0]

                            assemblies = post_api(ASSEMBLY_LIST_URL, {
                                'method': 'getAssemblyRevisionsByManualRev',
                                'use_ags_children': 1,
                                'manual_revision_id': entry['model_id'],
                                'assembly_group_schema_id': folder_id,
                                'sort': 'assembly_name',
                                'dir': 'ASC'
                            })

                            entry['folder_id'] = folder_id
                            entry['folder_name'] = folder_name

                            if assemblies and 'numFound' in assemblies and assemblies['numFound'] > 0:
                                for passembly in assemblies['assemblies']:
                                    assets_url = get_api(ASSEMBLY_ASSETS_URL + passembly['assembly_revision_id'])
                                    try:
                                        entry['image'] = assets_url['assembly_drawing_set']['assembly_drawing'][0]['diagram']
                                    except:
                                        entry['image'] = ''

                                    assembly_bmp = post_api(ASSEMBLY_LIST_URL, {
                                        'start': 0,
                                        'assembly_revision_id': passembly['assembly_revision_id'],
                                        'parent_bom_item_id': 0,
                                        'manual_revision_id': folder_id,
                                        'processFields[0]': 'parent',
                                        'processFields[1]': 'trackingInfo',
                                        'method': 'getAssemblyBomList',
                                    })

                                    if assembly_bmp and 'numFound' in assembly_bmp and assembly_bmp['numFound'] > 0:
                                        for pbom in assembly_bmp['bom']:
                                            entry['part_name'] = pbom['product_name']
                                            entry['description'] = pbom['name']
                                            entry['sku'] = pbom['sku']
                                            entry['quantity'] = pbom['quantity']
                                            entry['is_scraped'] = 1

                                            writer.writerow(entry)

                        except Exception as e:
                            print("Error!")
                            log("** line: 231 **: ")
                            log(e)
                print("Done!")
                driver.quit()
                csv_file.close()
            except Exception as e:
                print("Error!")
                log("** line: 237 **: ")
                log(e)
                driver.quit()
                csv_file.close()

