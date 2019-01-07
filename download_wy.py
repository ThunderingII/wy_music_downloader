import os
import re

import requests
import json

from hashlib import md5
from NEMbox.api import NetEase, Parse

MUSIC_DOWNLOAD_PATH = 'music_download'
LOVE_PLAYLIST_FILE = 'love_playlist.txt'

USERNAME = 'username@163.com'
PASSWORD = b'password'

headers = {
    'Cookie': 'Tip_of_the_day=2; encrypt_data=56f2bc9d081609eb8e605a176c9f144de8c9c6ac96288a2e51fce7143a94433d8c0c4fc70944b9163392d9ea977fc7343168112d1769b16d03bd4b9d7d56317224940c2824ccbeeccb73a633bdfeabdd7c124ff7f5064b6ef27b7959ebcb279cb52e5da22eff1a00fd6ee3efe7adc077a415e7bd0edfb126ed4487ef27904634; SL_GWPT_Show_Hide_tmp=1; SL_wptGlobTipTmp=1',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36',
    'X-Requested-With': 'XMLHttpRequest',
}

DEBUG = False

session = None


def get_download_url(urlid):
    url = 'http://moresound.tk/music/' + urlid
    res = session.get(url, headers=headers)
    return res.json()['url']


def save_as_file(urlid, save_name, suffix):
    print(f'开始下载:{save_name}{suffix}')
    if not os.path.exists(MUSIC_DOWNLOAD_PATH):
        os.mkdir(MUSIC_DOWNLOAD_PATH)
    if not os.path.exists(f'{MUSIC_DOWNLOAD_PATH}/{save_name}{suffix}'):
        url = get_download_url(urlid)
        res = session.get(url).content
        with open(f'{MUSIC_DOWNLOAD_PATH}/{save_name}{suffix}', 'wb')as f:
            f.write(res)


def download(id, platform):
    url = 'http://moresound.tk/music/api.php?get_song={}'.format(platform)
    data = {'mid': id}
    res = session.post(url, data=data, headers=headers)
    ss = res.json()

    download_preference = ['FLAC', 'APE', '320MP3', '192MP3', '128MP3',
                           '24AAC']

    dp_weights = {'FLAC': 9, 'APE': 9, '320MP3': 5, '192MP3': 4, '128MP3': 3,
                  '24AAC': 2}
    save_name = ss['song'] + '__' + ss['singer']
    # 正则去掉文件名不支持的字符
    save_name = re.sub('[\\\\/:*?\"<>|]', '', str(save_name))
    url_id = None
    suffix = None
    for df in download_preference:
        if df in ss['url']:
            url_id = ss['url'][df]
            if df == 'FLAC':
                suffix = '.flac'
            elif df == ['APE']:
                suffix = '.ape'
            else:
                suffix = '.mp3'
            return (url_id, save_name, suffix, dp_weights[df])
    return None


def search_and_download_music(name, ar_name, al_name):
    r_list = ['(', ')', '（', '）']
    data = {
        'w': f'{name}',
        'p': '1',
        'n': '5',
    }
    for r in r_list:
        name = name.replace(r, '.*')

    global session

    if session is None:
        session = requests.session()
        res = session.get('http://moresound.tk/music/')

        print(res.headers.get('Cookie'))
    platform_list = ['wy', 'qq', 'kw', 'xm', 'kg', 'bd']

    max_w = -1
    di = None
    for p in platform_list:
        url = 'http://moresound.tk/music/api.php?search={}'.format(p)
        res = session.post(url, data=data, headers=headers)
        ress = res.json()
        if not 'song_list' in ress:
            print(f'在{p}没有找到:{name}-{ar_name}')
            continue
        for song in ress['song_list'][:5]:
            singer = song['singer'][0]['name']
            songname = re.sub('<sup.*|\n.*|\r.*', '', song['songname'])
            albumname = song['albumname']
            songmid = song['songmid']
            if re.fullmatch(name, songname) and (
                    singer in ar_name or ar_name in singer):
                url_id, save_name, suffix, dw = download(songmid, p)
                if dw == 9:
                    print(f'在{p}找到:{name}{suffix}-{ar_name}')
                    save_as_file(url_id, save_name, suffix)
                    return
                elif dw > max_w:
                    max_w = dw
                    di = (url_id, save_name, suffix, p, dw)
                break
        else:
            if DEBUG:
                print(f'在{p}没有找到:{name}-{ar_name}')
                print('-' * 50)
                print(ress)
                print('-' * 50)

    if di:
        url_id, save_name, suffix, p, dw = di
        print(f'在{p}找到:{name}{suffix}-{ar_name}')
        save_as_file(url_id, save_name, suffix)


def main():
    fail_list = []

    if os.path.exists(LOVE_PLAYLIST_FILE):
        with open(LOVE_PLAYLIST_FILE, encoding='utf-8') as lpf:
            love_playlist = json.load(lpf)
    else:
        api = NetEase()
        user = api.login(USERNAME, md5(PASSWORD).hexdigest())
        print(user)
        user_id = user['account']['id']
        prase = Parse()
        ps = prase.playlists(api.user_playlist(user_id))

        love_playlist_id = [m for m in ps if
                            m['playlist_name'] == f"{m['creator_name']}喜欢的音乐"][
            0]['playlist_id']
        print(love_playlist_id)
        love_playlist = api.playlist_detail(love_playlist_id)
        with open(LOVE_PLAYLIST_FILE, mode='w', encoding='utf-8') as lpf:
            json.dump(love_playlist, lpf)
    for i, d in enumerate(love_playlist):
        try:
            search_and_download_music(d['name'], d['ar'][0]['name'],
                                      d['al']['name'])
            print(f'{i+1}/{len(love_playlist)} {d["name"]} 下载完成')
        except Exception as e:
            fail_list.append(d["name"])
            print(f'{i+1}/{len(love_playlist)} {d["name"]} 下载失败！！！！:{e}')
    print('-' * 20, '下载失败的歌曲', '-' * 20)
    print(fail_list)


if __name__ == '__main__':
    main()
