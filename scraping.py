import os
import time
import datetime

from selenium.webdriver import Chrome, ChromeOptions
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import fire
import pandas as pd

# Selenium version4対応済

# 定数は大文字の変数名が一般的
# {}に変数名をセットすると、後でformatで置換可能
LOG_FILE_PATH = "logs/log_{datetime}.log"
EXP_CSV_PATH="results/exp_list_{search_keyword}_{datetime}.csv"
log_file_path=LOG_FILE_PATH.format(datetime=datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S'))


def set_driver(hidden_chrome: bool=False):
    '''
    Chromeを自動操作するためのChromeDriverを起動してobjectを取得する
    '''
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Safari/537.36"
    options = ChromeOptions()

    # ヘッドレスモード（画面非表示モード）をの設定
    if hidden_chrome:
        options.add_argument('--headless')

    # 起動オプションの設定
    options.add_argument(f'--user-agent={USER_AGENT}') # ブラウザの種類を特定するための文字列
    options.add_argument('log-level=3') # 不要なログを非表示にする
    options.add_argument('--ignore-certificate-errors') # 不要なログを非表示にする
    options.add_argument('--ignore-ssl-errors') # 不要なログを非表示にする
    options.add_experimental_option('excludeSwitches', ['enable-logging']) # 不要なログを非表示にする
    options.add_argument('--incognito') # シークレットモードの設定を付与
    
    # ChromeのWebDriverオブジェクトを作成する。(Selenium version4からは以下のようにServiceを使用することが推奨される)
    service=Service(ChromeDriverManager().install())
    return Chrome(service=service, options=options)


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


def find_table_col_by_header_name(th_elms, td_elms, target:str):
    '''
    table要素の中から、targetで指定したheaderを探し、対応するカラムのdataを取得する
    '''
    # tableのthからtargetの文字列を探し一致する行のtdを返す
    for th_elm,td_elm in zip(th_elms,td_elms):
        if th_elm.text == target:
            return td_elm.text


def main(is_option: bool = False, page_limit: int=5, hidden_chrome: bool=False):
    '''
    main処理
     - is_option: Trueでオプション課題用のurlの直接指定機能を動作させる
     - page_limit: スクレピングするページ数の上限を指定
    '''
    log(f"処理開始: is_option={is_option}, page_limit={page_limit}, hidden_chrome={hidden_chrome}")
    search_keyword=input("検索キーワードを入力してください：")
    log("検索キーワード:{}".format(search_keyword))
    # driverを起動
    driver = set_driver(hidden_chrome)
    
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
        # Selenium version4からfind_element_by_*のメソッドは非推奨となったため、以下の通りfind_elementを使用
        driver.find_element(by=By.CLASS_NAME, value="topSearch__text").send_keys(search_keyword)
        # 検索ボタンクリック
        driver.find_element(by=By.CLASS_NAME, value="topSearch__button").click()

    # ページ終了まで繰り返し取得
    count = 0
    success = 0
    fail = 0
    page = 1
    recruits = []
    while page <= page_limit:
        # 求人の要素を丸ごと取得
        recruit_elms = driver.find_elements(by=By.CSS_SELECTOR, value=".cassetteRecruit")
        '''
        ## 色々な指定方法
        by=By.CSS_SELECTOR のようにして指定方法を選択
        By.ID By.NAME By.CLASS_NAME By.LINK_TEXT などがあるので
        Byと入力して、VSCODEの予測変換で確認してみると良いと思います。
        概ねCSS_SELECTORで網羅できるので基本はCSS_SELECTORを推奨ですが
        NAMEはSELECTORで指定すると面倒なので、NAMEを使った方が楽です。
        '''
        
        # 1ページ分繰り返し
        for recruit_elm in recruit_elms:
            # try~exceptはエラーの可能性が高い箇所に配置
            try:
                name = recruit_elm.find_element(by=By.CSS_SELECTOR, value=".cassetteRecruit__name").text
                copy = recruit_elm.find_element(by=By.CSS_SELECTOR, value=".cassetteRecruit__copy").text
                employment_status = recruit_elm.find_element(by=By.CSS_SELECTOR, value=".labelEmploymentStatus").text
                table_elm = recruit_elm.find_element(by=By.CSS_SELECTOR, value="table")
                # 初年度年収をtableから探す
                first_year_fee = find_table_col_by_header_name(table_elm.find_elements(by=By.TAG_NAME, value="th"), table_elm.find_elements(by=By.TAG_NAME, value="td"), "初年度年収")
                # DataFrameにレコードを追加(辞書形式でセット)
                recruits.append(
                    {
                        "企業名": name,
                        "キャッチコピー": copy,
                        "ステータス": employment_status,
                        "初年度年収": first_year_fee
                    }
                )
                log(f"[成功]{count} 件目 (page: {page}) : {name}")
                success+=1
            except Exception as e:
                log(f"[失敗]{count} 件目 (page: {page})")
                log(e)
                fail+=1
            finally:
                # finallyは成功でもエラーでも必ず実行
                count+=1

        # 次のページボタンがあればリンクを取得して画面遷移、なければ終了
        next_page = driver.find_elements(by=By.CLASS_NAME, value="iconFont--arrowLeft")
        # if len(next_page) >= 1: # Python公式として非推奨の方式となったため変更
        if next_page:
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
    # df.appendは非推奨になったため、from_dictを使用する
    df = pd.DataFrame.from_dict(recruits, dtype=object)
    df.to_csv(EXP_CSV_PATH.format(search_keyword=search_keyword, datetime=now), encoding="utf-8-sig")
    
    # ログの役割は、開発時や後からプログラムの動作をチェックするために用いる
    # ログがないと、お客から何か動作がおかしいと指摘されても、確認するすべがない。
    log(f"処理完了 成功件数: {success} 件 / 失敗件数: {fail} 件")

    
# 直接起動された場合はmain()を起動(モジュールとして呼び出された場合は起動しないようにするため)
if __name__ == "__main__":
    '''
    課題の範囲ではないが、引数を簡単に処理できるので便利
    - 以下ように指定できる（例：is_option=True, page_limit=3 と指定される）
     python scraping.py 1 3
    - 一部の引数のみの指定も可能(chromeを非表示) ハイフン２個と変数名で指定する
     python scraping.py --hidden-chrome
    '''
    fire.Fire(main)
              
    
    


