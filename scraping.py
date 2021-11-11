import os
import time
import pandas as pd
import datetime
from selenium.webdriver import Chrome, ChromeOptions
from webdriver_manager.chrome import ChromeDriverManager
import fire

# 定数は大文字の変数名が一般的
# {}に変数名をセットすると、後でformatで置換可能
LOG_FILE_PATH = "logs/log_{datetime}.log"
EXP_CSV_PATH="results/exp_list_{search_keyword}_{datetime}.csv"
log_file_path=LOG_FILE_PATH.format(datetime=datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S'))


def set_driver(driver_path, headless_flg):
    '''
    Selenium用のChromeを起動する
    '''
    # Chromeドライバーの読み込み
    options = ChromeOptions()

    # ヘッドレスモード（画面非表示モード）をの設定
    if headless_flg == True:
        options.add_argument('--headless')

    # 起動オプションの設定
    # User-agentはブラウザと同様のものを使用する。指定しないとサイトによってはブロックされる可能性がある
    options.add_argument(
        '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.116 Safari/537.36')
    
    # 不要なエラーを非表示にする
    options.add_argument('log-level=3')
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--ignore-ssl-errors')
    options.add_argument('--incognito') # シークレットモードの設定を付与

    # ChromeのWebDriverオブジェクトを作成する。
    # ChromeDriverManager().install() はChromeDriverの最新版をdownloadして、そのPATHを返す
    return Chrome(ChromeDriverManager().install(), options=options)


def makedir_for_filepath(filepath: str):
    '''
    ファイルを格納するフォルダを作成する
    '''
    # exist_ok=Trueとすると、フォルダが存在してもエラーにならない
    os.makedirs(os.path.dirname(filepath), exist_ok=True)


def log(txt):
    '''
    ログファイルおよびコンソール出力
    (学習用に１から作成しているが、通常はloggingライブラリを推奨)
    '''
    now = datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
    logStr = '[%s: %s] %s' % ('log',now , txt)
    # ログ出力
    makedir_for_filepath(log_file_path)
    with open(log_file_path, 'a', encoding='utf-8_sig') as f:
        f.write(logStr + '\n')
    print(logStr)


def find_table_target_word(th_elms, td_elms, target:str):
    '''
    table要素の中から、targetで指定したheaderを探し、対応するdataを取得する
    '''
    # tableのthからtargetの文字列を探し一致する行のtdを返す
    for th_elm,td_elm in zip(th_elms,td_elms):
        if th_elm.text == target:
            return td_elm.text


def main(is_option: bool = False, page_limit: int=5):
    '''
    main処理
     - is_option: Trueでオプション課題用のurlの直接指定機能を動作させる
     - page_limit: スクレピングするページ数の上限を指定
    '''
    log(f"処理開始: is_option={is_option}, page_limit={page_limit}")
    search_keyword=input("検索キーワードを入力してください：")
    log("検索キーワード:{}".format(search_keyword))
    # driverを起動
    driver = set_driver("chromedriver.exe", False)
    
    # Webサイトを開く
    if is_option:
        # Option課題の場合は、URLを直接編集する
        driver.get(f"https://tenshoku.mynavi.jp/list/kw{search_keyword}/?jobsearchType=14&searchType=18")
        time.sleep(5)
    else:
        driver.get("https://tenshoku.mynavi.jp/")
        time.sleep(5)
        try:
            # ポップアップを閉じる（seleniumだけではクローズできない）
            driver.execute_script('document.querySelector(".karte-close").click()')
            time.sleep(5)
            # ポップアップを閉じる
            driver.execute_script('document.querySelector(".karte-close").click()')
        except:
            pass

        # 検索窓に入力
        driver.find_element_by_class_name("topSearch__text").send_keys(search_keyword)
        # 検索ボタンクリック
        driver.find_element_by_class_name("topSearch__button").click()

    # ページ終了まで繰り返し取得
    count = 0
    success = 0
    fail = 0
    df = pd.DataFrame()
    page = 1
    while page <= page_limit:
        # 求人の要素を丸ごと取得
        recruit_elms = driver.find_elements_by_css_selector(".cassetteRecruit")
        
        '''
        ## 様々なCSSセレクター
        driver.find_elements_by_css_selector(".classname tagname") #クラス配下のタグ
        driver.find_elements_by_css_selector(".classname>tagname") #クラス直下のタグ
        driver.find_elements_by_css_selector("[name='test']") #name属性=test
        driver.find_elements_by_css_selector("[data-test='test-data']") #data-test属性=test-data
        '''
        
        # 1ページ分繰り返し
        for recruit_elm in recruit_elms:
            try:
                name = recruit_elm.find_element_by_css_selector(".cassetteRecruit__name").text
                copy = recruit_elm.find_element_by_css_selector(".cassetteRecruit__copy").text
                employment_status = recruit_elm.find_element_by_css_selector(".labelEmploymentStatus").text
                table_elm = recruit_elm.find_element_by_css_selector("table")
                # try~exceptはエラーの可能性が高い箇所に配置
                # 初年度年収をtableから探す
                first_year_fee = find_table_target_word(table_elm.find_elements_by_tag_name("th"), table_elm.find_elements_by_tag_name("td"), "初年度年収")
                # DataFrameにレコードを追加(辞書形式でセット)
                df = df.append({"企業名": name,
                                "キャッチコピー": copy,
                                "ステータス": employment_status,
                                "初年度年収": first_year_fee},
                                ignore_index=True)
                log(f"[成功]{count} 件目 (page: {page}) : {name}")
                success+=1
            except Exception as e:
                log(f"[失敗]{count} 件目 (page: {page}): {name}")
                log(e)
                fail+=1
            finally:
                # finallyは成功でもエラーでも必ず実行
                count+=1


        # 次のページボタンがあればリンクを取得して画面遷移、なければ終了
        next_page = driver.find_elements_by_class_name("iconFont--arrowLeft")
        if len(next_page) >= 1:
            next_page_link = next_page[0].get_attribute("href")
            driver.get(next_page_link)
        else:
            log("最終ページです。終了します。")
            break
        
        page += 1

    # 現在時刻を指定した文字列フォーマットとして取得（非常によく使う）
    now = datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
    # csv出力（encodingはWindowsのExcelの文字化け防止のためにutf-8-sig(BOM付きUTF8)とする
    makedir_for_filepath(EXP_CSV_PATH)
    df.to_csv(EXP_CSV_PATH.format(search_keyword=search_keyword, datetime=now), encoding="utf-8-sig")
    
    # ログの役割は、開発時や後からプログラムの動作をチェックするために用いる
    # ログがないと、お客から何か動作がおかしいと指摘されても、確認するすべがない。
    log(f"処理完了 成功件数: {success} 件 / 失敗件数: {fail} 件")
    
    
# 直接起動された場合はmain()を起動(モジュールとして呼び出された場合は起動しないようにするため)
if __name__ == "__main__":
    # 課題の範囲ではないが、引数を簡単に処理できるので便利
    # 以下ように指定できる（例：is_option=True, page_limit=3 と指定される）
    # python scraping.py 1 3
    fire.Fire(main)
              
    
    


