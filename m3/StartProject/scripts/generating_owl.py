from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
import requests
import os

def run():
    dir_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "resources")
    driver = webdriver.Chrome()
    driver.get("http://ontorat.hegroup.org/index.php")

    # adding the settings file
    assert "Ontorat" in driver.title
    elem = driver.find_element_by_id("settings_file")
    elem.send_keys(dir_path + "\\ontorat_settings.txt")
    driver.find_element_by_name("Submit1").click()

    # loading previous owl
    '''
    elem = driver.find_element_by_id("target_owl")
    elem.send_keys(dir_path+"\\y8apyswx_out.owl.xml")
    '''
    # loading data file
    elem = driver.find_element_by_id("data_file")
    elem.send_keys(dir_path + "\\ontorat_input_file.txt")
    driver.find_elements_by_name("Submit1")[1].click()

    driver.implicitly_wait(5)
    driver.switch_to.window(driver.window_handles[1])
    driver.find_element_by_partial_link_text("output").click()

    driver.switch_to.window(driver.window_handles[2])


    def download_file(url):
        #local_filename = url.split('/')[-1]
        local_filename = os.path.join(dir_path, "generated_ontology.owl")
        print(local_filename)
        # NOTE the stream=True parameter
        r = requests.get(url, stream=True)
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:  # filter out keep-alive new chunks
                    f.write(chunk)
                    # return local_filename


    download_file(driver.current_url)
    driver.quit()
    # driver.quit()
    # exit()

if __name__ == '__main__':
    run()