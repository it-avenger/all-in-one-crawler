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

from lxml import etree, html
import pdb

CRALWER_NAME = "agroparts"
DOMAIN = 'https://www.agroparts.com'

logging.basicConfig(filename="logs/{}.log".format(CRALWER_NAME))

#Creating an object
logger=logging.getLogger()
logger.setLevel(logging.INFO)

now = datetime.now()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CSV_HEADERS = ['field', 'category', 'sub_category', 'model']


def post_api(url, payload):
    try:
        r = requests.post(url, data=payload)
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

def wait_until_loading(driver, xpath, interval=30):
    wait = WebDriverWait(driver, interval)
    element = wait.until(EC.visibility_of_element_located((By.XPATH, xpath)))
    return element

def click_links(driver, links_xpath, target_link, text_type="title"):
    source = driver.page_source.encode("utf8")
    tree = etree.HTML(source)
    brands = tree.xpath(links_xpath)
    is_brand = False
    brand_link = ''
    for brand in brands:
        brand_title = ''
        if text_type == "title":
            brand_title = brand.xpath("./@title")[0]
        else:
            brand_title = brand.xpath(".//text()")[0]

        if target_link in brand_title:
            brand_link = brand.xpath("./@href")[0]
            abs_path = etree.ElementTree(tree).getpath(brand)
            driver.find_element_by_xpath(abs_path).click()
            driver.switch_to.window(driver.window_handles[1])
            is_brand = True
            break

    if is_brand == False:
        print("Error!")
        log("There is no {} link:".format(target_link))
    # driver.get(DOMAIN + brand_link)

if __name__ == "__main__":
    results = []
    number_of_results = 0
    ext_models = []
    output_path = "{}/output/{}_output".format(BASE_DIR, CRALWER_NAME)
    model_file_path = "{}/output/{}_model.csv".format(BASE_DIR, CRALWER_NAME)
    csv_path = "{}/{}.csv".format(BASE_DIR, CRALWER_NAME)
    is_all = False
    target_brand = 'Accord'
    models = []
    dedicated_url = '' # url for each brand on agroparts

    if not os.path.exists(output_path):
        os.makedirs(output_path)

    if not os.path.exists(csv_path):
        with open(csv_path, mode='w', newline='') as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=CSV_HEADERS)
            writer.writeheader()

    run_type = "model"
    if len(sys.argv) > 1 and sys.argv[1] == "output":
        run_type = "output"

    with open(csv_path) as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            if 'model_id' in row and row['model_id'] not in ext_models:
                ext_models.append(row['model_id'])

    # define selenium driver
    driver = webdriver.Chrome(executable_path=BASE_DIR+"/chromedriver.exe")
    driver.set_window_size(1850, 1000)

    # login
    login_url = 'https://www.agroparts.com/agroparts/homepage'
    email_xpath = '//input[@name="username"]'
    password_xpath = '//input[@name="password"]'
    login_btn_xpath = '//form[@id="login-form"]//input[@type="submit"]'

    try:
        driver.get(login_url)
        login_btn = wait_until_loading(driver, login_btn_xpath)

        driver.find_element_by_xpath(email_xpath).send_keys("mverbaan@yandex.com")
        driver.find_element_by_xpath(password_xpath).send_keys("test1234")
        login_btn.click()

        wait_until_loading(driver, '//div[contains(@class, "brands")]')

        source = driver.page_source.encode("utf8")
        tree = etree.HTML(source)
        seesion_prompt = tree.xpath('//div[@id="session-squeeze-out-prompt"]')
        pdb.set_trace()
        if len(seesion_prompt) > 0:
            time.sleep(1)
            driver.find_element_by_xpath('//button[@id="login-override-session-button"]').click()
            wait_until_loading(driver, '//div[contains(@class, "brands")]')

        # additional step for this website, which finds brands
        brands_xpath = '//div[contains(@class, "brands")]//a[@class="brand-spacing"]'
        click_links(driver, brands_xpath, target_brand)
        time.sleep(5)

        # click "OnlineCatalog"
        click_links(driver, '//ul[@id="brand-menu"]//li//a', 'OnlineCatalog', 'text')
        wait_until_loading(driver, '//table[@class="list"]')
        # time.sleep(5)

    except Exception as e:
        print("line: 145")
        print(e)
        print("Error!")


    if run_type == "model":
        source = driver.page_source.encode("utf8")
        tree = etree.HTML(source)
        categories = tree.xpath('//table[@class="list"]//tbody//tr')
        for pcategory in categories:
            item = dict()
            category_name = pcategory.xpath(".//a/text()")[0].strip()
            category_link = pcategory.xpath(".//a/@href")

            item['category'] = category_name

            abs_path = etree.ElementTree(tree).getpath(category_link)
            driver.find_element_by_xpath(abs_path).click()


            source = driver.page_source.encode("utf8")
            tree = etree.HTML(source)
            categories = tree.xpath('(//table[@class="list"])[2]//tbody')
            for psub_category in sub_categories:
                item = dict()
                subcat_name = psub_category.xpath(".//a/text()")[0].strip()
                subcat_link = psub_category.xpath(".//a/@href")

                item['sub_category'] = subcat_name

                sub_abs_path = etree.ElementTree(tree).getpath(subcat_link)
                driver.find_element_by_xpath(sub_abs_path).click()


                source = driver.page_source.encode("utf8")
                tree = etree.HTML(source)
                categories = tree.xpath('(//table[@class="list"])[2]//tbody')
                for pmachine in machines:
                    item = dict()
                    machine_name = pmachine.xpath(".//a/text()")[0].strip()
                    machine_link = pmachine.xpath(".//a/@href")[0]

                    item['machine'] = machine_name
                    item['machine_url'] = machine_link
                    models.append(item)


        with open(model_file_path, mode='w', newline='') as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=CSV_HEADERS)
            writer.writeheader()
            for pmodel in models:
                driver.get(dedicated_url+pmodel['device_url'])
                pdb.set_trace()



