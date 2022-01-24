#!/usr/bin/python3
import os
import shutil
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import StaleElementReferenceException

from zipfile import ZipFile
import img2pdf
from merge_pdf import merge

# if not sys.warnoptions:
# 	import warnings
# 	warnings.simplefilter("ignore")

class mangaParser(object):

	def __init__ (self, driver, link, login, pwd, path):
		self.driver = driver
		self.link = link
		self.login = login
		self.pwd = pwd
		self.path = path

	def parseChapters(self):
		# Получаю количество глав
		numOfChapters = WebDriverWait(self.driver, 60).until(EC.presence_of_element_located((By.ID, 'main-page')))
		numOfChapters = numOfChapters.find_elements(By.CLASS_NAME, 'text-capitalize')[1].text
		self.numOfChapters = int(numOfChapters)

		# Получаю количество томов
		numOfToms = self.driver.find_element(By.XPATH, '//div[contains(@class, "vue-recycle-scroller")]/div[contains(@class, "vue-recycle-scroller__item-wrapper")]')
		self.numOfToms = int(numOfToms.find_element(By.XPATH, '//div[1]//div[@class="media-chapter"]//div[@class="media-chapter__body"]//div[@class="media-chapter__name text-truncate"]//a[@class="link-default"]').text.split('Том ')[1].split(' ')[0])
		
		# Открываю модальное окно для авторизации
		auth = WebDriverWait(self.driver, 60).until(EC.presence_of_element_located((By.CLASS_NAME, 'header')))
		auth = auth.find_element(By.ID, 'show-login-button')
		auth.click()

		# Нахожу форму и обёрточные блоки для логина и пароля
		formFields = self.driver.find_elements(By.XPATH, '//form[@id="sign-in-form"]/div[@class="form__field"]')[0:2]

		# Заполняю поле логина входным логином пользователя
		inputLogin = formFields[0].find_element(By.CLASS_NAME, 'form__input-wrap')
		inputLogin = inputLogin.find_element(By.CLASS_NAME, 'form__input')
		inputLogin.clear()
		inputLogin.send_keys(self.login)

		# Заполняю поле пароля входным паролем пользователя
		inputPassword = formFields[1].find_element(By.CLASS_NAME, 'form__input-wrap')
		inputPassword = inputPassword.find_element(By.CLASS_NAME, 'form__input')
		inputPassword.clear()
		inputPassword.send_keys(self.pwd)

		# Кликаю по кнопке входа
		btn = self.driver.find_element(By.XPATH, '//div[@class="form__footer"]/button')
		btn.click()
		time.sleep(3)

		# Жду, пока прогрузится страница
		self.driver.refresh()
		ignored_exceptions=(NoSuchElementException,StaleElementReferenceException,)
		WebDriverWait(self.driver, 60, ignored_exceptions=ignored_exceptions).until(EC.presence_of_element_located((By.CLASS_NAME, 'media-section')))
		try:
			self.driver.execute_script('document.getElementsByClassName("container")[0].setAttribute("style", "padding: 0px")')
			self.driver.execute_script('document.getElementsByClassName("media-chapters-list__footer")[0].setAttribute("style", "text-align: left;")')
		except:
			pass

		self.driver.find_element(By.CLASS_NAME, 'media-chapters-sort').click()
		time.sleep(2)

		# Нахожу блок с главами и создаю список видимых глав
		self.driver.implicitly_wait(5)
		wrapper = self.driver.find_element(By.XPATH, '//div[contains(@class, "vue-recycle-scroller")]//div[contains(@class, "vue-recycle-scroller__item-wrapper")]')
		startWith = wrapper.find_element(By.XPATH, '//div[1]//div[@class="media-chapter"]//div[@class="media-chapter__body"]//div[@class="media-chapter__name text-truncate"]//a[@class="link-default"]').text.split('Глава ')[1]
		startWith = int(startWith.split(' ')[0]) if ' ' in startWith else int(startWith)

		# Определяю список просмотренных глав, количество глав в последнем томе, временнную переменную для сохранения количества глав в томе, итератор глав
		listOfCheckedChapters = []
		numChInLastTom = 0
		tmpNumChInLastTom = 0
		counterChapter = startWith
		for i in range(0, self.numOfChapters):
			# Получаю список видимых обёрток глав
			chapters = wrapper.find_elements(By.XPATH, '//div[contains(@class, "vue-recycle-scroller__item-view")]')
			for ch in chapters:
				# Определяю имя и номер главы
				try:
					chapterName = ch.find_element(By.XPATH, '//div[@class="media-chapter"]//div[@class="media-chapter__body"]//div[@class="media-chapter__name text-truncate"]/a[@class="link-default"]')
					numOfChapter = chapterName.text.split('Глава ')[1]
				except:
					return
				if ' ' in numOfChapter:
					numOfChapter = numOfChapter.split(' ')[0]			
				if numOfChapter == str(counterChapter - numChInLastTom) or ('.' in numOfChapter and float(counterChapter - numChInLastTom) - float(numOfChapter) <= 1.0):
					btn = ch.find_element(By.XPATH, '//div[@class="media-chapter"]//div[@class="media-chapter__actions"]//div[@aria-label="Скачать главу"]')					
					btn.click()
					tmpNumChInLastTom = i
					listOfCheckedChapters.append(btn)
					counterChapter += 1
					# Чтобы из-за экстра глав следующая глава не пропускалась  
					if '.' in numOfChapter:
						counterChapter -= 1
				# !!! Есть вероятность, что ниже в elif, как и, наверно, везде, говнокод
				elif numOfChapter == '1' and counterChapter > 1:
					numChInLastTom = tmpNumChInLastTom
					btn = ch.find_element(By.XPATH, '//div[contains(@class, "media-chapter")]//div[@class="media-chapter__actions"]//div[@aria-label="Скачать главу"]')					
					btn.click()
					listOfCheckedChapters.append(btn)
					counterChapter += 1
				else:
					continue
			# Каждые 10 глав я жду, пока они скачаются
			if i % 10 == 0:
				while True:
				# Очищаю список просмотренных, если главы скачаны
					for checkedChapter in listOfCheckedChapters:
						if checkedChapter.get_attribute('data-status') == 'complete':
							listOfCheckedChapters.remove(checkedChapter)
					# Условие выхода из цикла, если все главы скачаны
					if len(listOfCheckedChapters) == 0:
						break
		# Проверяю, что все главы скачаны 
		if len(listOfCheckedChapters) != 0:
			while True:
				# Очищаю список просмотренных, если главы скачаны
					for checkedChapter in listOfCheckedChapters:
						if checkedChapter.get_attribute('data-status') == 'complete':
							listOfCheckedChapters.remove(checkedChapter)
					# Условие выхода из цикла (если все главы скачаны), также увеличиваю переменную скачанных глав 
					if len(listOfCheckedChapters) == 0:
						break
		time.sleep(5)

	def unzipFiles(self):
		# прохожу по списку и распаковываю каждый zip-файл с названием без [mangalib.me] и удаляю zip-файл
		listOfZipFiles = os.listdir(self.path)
		for file in listOfZipFiles:
			zf = ZipFile(os.path.join(self.path, file), 'r')
			zf.extractall(os.path.join(self.path, file)[0:-18])
			zf.close()
			os.remove(os.path.join(self.path, file))

	def convertJpg2Pdf(self):
		# Создаю список директорий с изображениями и прохожу в цикле по каждой директории
		listOfDirs = sorted(os.listdir(self.path), key=lambda x: float(x.split('Глава ')[1]))
		for dirOfFiles in listOfDirs:
			# Список изображений
			files = sorted(os.listdir(os.path.join(self.path, dirOfFiles)), key=lambda x: float(x.split('.')[0]))
			# Файл pdf, в который соберу все изображения и он будет на уровне директории
			pdf = os.path.join(self.path, dirOfFiles) + '.pdf'
			# Создаю список абсолютных путей к изображениям
			pathsOfFiles = []
			for file in files:
				pathsOfFiles.append(os.path.join(self.path, dirOfFiles, file))
			# Конвертирую все изображения в один pdf 
			with open(pdf, 'wb') as f:
				f.write(img2pdf.convert([i for i in pathsOfFiles]))
			# Удаляю директорию и всё содержимое
			shutil.rmtree(os.path.join(self.path, dirOfFiles))

	def mergePdf(self):
		# Создаю список всех глав в папке
		files = sorted(os.listdir(self.path), key=lambda x: float(x.split('Глава ')[1].split('.')[0]))
		name = self.path.split('/').pop()
		# Цикл по томам, так как собираю главы в томы
		for i in range(1, self.numOfToms + 1):
			tom = []
			# Проверяю, что глава принадлежит текущему тому и добавляю его в список глав этого тома
			for file in files:
				if '0'*(len(str(self.numOfToms)) - len(file.split('Том ')[1].split(' ')[0])) + str(i) == file.split('Том ')[1].split(' ')[0]:
					tom.append(os.path.join(self.path, file))
			# Собираю все главы в один том
			outputFile = os.path.join(self.path, name + ' Том ' + str(i) + '.pdf')
			merge.Merge(outputFile, replace=True).merge_file_list(tom)
			# Убираю из списка всех глав главы текущего тома 
			files = [el for el in files if i not in tom]
			# Удаляю оставшиеся главы, которые я уже собрал в том
			for file in tom:
				os.remove(os.path.join(self.path, file))

def main():
	mangaTitle = str(input('Введите название тайтла в корректном формате: ')).strip()
	# Если папки нет, то создаю её
	try:
		os.stat(mangaTitle)
	except:
		os.mkdir(mangaTitle)

	path = os.path.join(os.getcwd(), mangaTitle) 

	# Логин и пароль от аккаунта в мангалиб
	# print('Пожалуйста, введите существующий аккаунт в mangalib.')
	login = str(input('Логин: ')).strip()
	pwd = str(input('Пароль: ')).strip()

	# Ссылка на вкладку глав тайтла в мангалибе
	link = str(input('Вставьте ссылку на сайт с главами (оканчивается на section=chapters): ')).strip()
	isByToms = str(input('Хотите соединить главы по томам? (Да/Нет): ')).strip().lower()


	# Опции для вебдрайвера. Убираю разрешение на скачивание и даю путь, куда нужно скачивать
	options = webdriver.ChromeOptions()
	# options.add_argument("--headless")
	options.add_experimental_option("prefs", {
    'download.default_directory': path,
    'profile.default_content_settings.popups': 0,
    'profile.content_settings.exceptions.automatic_downloads.*.setting': 1,
    'download.prompt_for_download': False
    })
	cap = webdriver.DesiredCapabilities.CHROME.copy()
	cap['ACCEPT_SSL_CERTS'] = True
	cap['CAPABILITY'] = options
	driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
	driver.maximize_window()
	driver.get(link)

	manga = mangaParser(driver, link, login, pwd, path)

	print('Скачиваю главы. Ждите...')
	manga.parseChapters()
	print('Распаковываю главы...')
	manga.unzipFiles()
	# manga.renameAll()
	print('Конвертирую главы в pdf...')
	manga.convertJpg2Pdf()
	if isByToms == 'да' or isByToms == 'yes':
		print('Объединяю главы по томам...')
		manga.mergePdf()

if __name__ == '__main__':
	main()