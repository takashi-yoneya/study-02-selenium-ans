import os
import time
import pandas as pd
import datetime
from selenium.webdriver import Chrome, ChromeOptions
from webdriver_manager.chrome import ChromeDriverManager

LOG_FILE_PATH = "./log/log_{datetime}.log"
EXP_CSV_PATH="./exp_list_{search_keyword}_{datetime}.csv"
log_file_path=LOG_FILE_PATH.format(datetime=datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S'))

### Chromeを起動する関数
def set_driver(driver_path, headless_flg):
    # Chromeドライバーの読み込み
    options = ChromeOptions()

    # ヘッドレスモード（画面非表示モード）をの設定
    if headless_flg == True:
        options.add_argument('--headless')

    # 起動オプションの設定
    options.add_argument(
        '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.116 Safari/537.36')
    # options.add_argument('log-level=3')
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--ignore-ssl-errors')
    options.add_argument('--incognito') # シークレットモードの設定を付与

    # ChromeのWebDriverオブジェクトを作成する。
    return Chrome(ChromeDriverManager().install(), options=options)

### ログファイルおよびコンソール出力
def log(txt):
    now = datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
    logStr = '[%s: %s] %s' % ('log',now , txt)
    # ログ出力
    with open(log_file_path, 'a', encoding='utf-8_sig') as f:
        f.write(logStr + '\n')
    print(logStr)


def find_table_target_word(th_elms, td_elms, target:str):
    # tableのthからtargetの文字列を探し一致する行のtdを返す
    for th_elm,td_elm in zip(th_elms,td_elms):
        if th_elm.text == target:
            return td_elm.text


### main処理
def main():
    log("処理開始")
    search_keyword=input("検索キーワードを入力してください：")
    log("検索キーワード:{}".format(search_keyword))
    # driverを起動
    driver = set_driver("chromedriver.exe", False)
    # Webサイトを開く
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
    while True:
        # 検索結果の一番上の会社名を取得(まれに１行目が広告の場合、おかしな動作をするためcassetteRecruit__headingで広告を除外している)
        name_list = driver.find_elements_by_css_selector(".cassetteRecruit__heading .cassetteRecruit__name")
        copy_list = driver.find_elements_by_css_selector(".cassetteRecruit__heading .cassetteRecruit__copy")
        status_list = driver.find_elements_by_css_selector(".cassetteRecruit__heading .labelEmploymentStatus")
        table_list = driver.find_elements_by_css_selector(".cassetteRecruit .tableCondition") # 初年度年収
        
        '''
        ## 様々なCSSセレクター
        driver.find_elements_by_css_selector(".classname tagname") #クラス配下のタグ
        driver.find_elements_by_css_selector(".classname>tagname") #クラス直下のタグ
        driver.find_elements_by_css_selector("[name='test']") #name属性=test
        driver.find_elements_by_css_selector("[data-test='test-data']") #data-test属性=test-data
        '''
        
        # 1ページ分繰り返し
        for name, copy, status, table in zip(name_list, copy_list, status_list,table_list):
            try:
                # try~exceptはエラーの可能性が高い箇所に配置
                # 初年度年収をtableから探す
                first_year_fee = find_table_target_word(table.find_elements_by_tag_name("th"), table.find_elements_by_tag_name("td"), "初年度年収")
                # DataFrameにレコードを追加
                df = df.append({"企業名": name.text,
                                "キャッチコピー": copy.text,
                                "ステータス": status.text,
                                "初年度年収": first_year_fee},
                                ignore_index=True)
                log(f"{count}件目成功 : {name.text}")
                success+=1
            except Exception as e:
                log(f"{count}件目失敗 : {name.text}")
                log(e)
                fail+=1
            finally:
                # finallyは成功でもエラーでも必ず実行
                count+=1

        # 次のページボタンがあればクリックなければ終了
        next_page = driver.find_elements_by_class_name("iconFont--arrowLeft")
        if len(next_page) >= 1:
            next_page_link = next_page[0].get_attribute("href")
            driver.get(next_page_link)
        else:
            log("最終ページです。終了します。")
            break

    # 現在時刻を指定した文字列フォーマットとして取得（非常によく使う）
    now = datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
    '''
    pd.DataFrame(辞書形式のデータ)
    辞書は以下の形式
    {
        "カラム名１":データのlist,
        "カラム名２":データのlist,
    }
    辞書　→　名前でアクセス可能　dic["企業名"]
    list　→　index番号でアクセス可能 li[1]
    
    通常はlistと辞書は組み合わせて使う
    '''
    # csv出力
    df.to_csv(EXP_CSV_PATH.format(search_keyword=search_keyword, datetime=now), encoding="utf-8-sig")
    
    # ログの役割は、開発時や後からプログラムの動作をチェックするために用いる
    # ログがないと、お客から何か動作がおかしいと指摘されても、確認するすべがない！
    log(f"処理完了 成功件数: {success} 件 / 失敗件数: {fail} 件")
    
# 直接起動された場合はmain()を起動(モジュールとして呼び出された場合は起動しないようにするため)
if __name__ == "__main__":
    main()
    
    


