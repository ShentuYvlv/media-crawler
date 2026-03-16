import json
import os
import re
import time
import openpyxl
import requests
from loguru import logger
from retry import retry

FIELD_LABELS = {
    'work_id': '作品id',
    'work_url': '作品url',
    'work_type': '作品类型',
    'title': '作品标题',
    'desc': '描述',
    'admire_count': 'admire数量',
    'digg_count': '点赞数量',
    'comment_count': '评论数量',
    'collect_count': '收藏数量',
    'share_count': '分享数量',
    'video_addr': '视频地址url',
    'images': '图片地址url列表',
    'topics': '标签',
    'create_time': '上传时间',
    'video_cover': '视频封面url',
    'user_url': '用户主页url',
    'user_id': '用户id',
    'nickname': '昵称',
    'author_avatar': '头像url',
    'user_desc': '用户描述',
    'following_count': '关注数量',
    'follower_count': '粉丝数量',
    'total_favorited': '作品被赞和收藏数量',
    'aweme_count': '作品数量',
    'user_age': '用户年龄',
    'gender': '性别',
    'ip_location': 'ip归属地',
}

SEARCH_EXCLUDED_FIELDS = {
    'following_count',
    'follower_count',
    'total_favorited',
    'aweme_count',
    'user_age',
    'gender',
    'ip_location',
    'images',
    'admire_count',
    'work_id',
}


def norm_str(str):
    new_str = re.sub(r"|[\\/:*?\"<>| ]+", "", str).replace('\n', '').replace('\r', '')
    return new_str

def norm_text(text):
    ILLEGAL_CHARACTERS_RE = re.compile(r'[\000-\010]|[\013-\014]|[\016-\037]')
    text = ILLEGAL_CHARACTERS_RE.sub(r'', text)
    return text


def timestamp_to_str(timestamp):
    time_local = time.localtime(timestamp / 1000)
    dt = time.strftime("%Y-%m-%d %H:%M:%S", time_local)
    return dt



def handle_work_info(data):
    sec_uid = data['author']['sec_uid']
    user_url = f'https://www.douyin.com/user/{sec_uid}'
    user_desc = data['author']['signature'] if 'signature' in data['author'] else '未知'
    following_count = data['author']['following_count'] if 'following_count' in data['author'] else '未知'
    follower_count = data['author']['follower_count'] if 'follower_count' in data['author'] else '未知'
    total_favorited = data['author']['total_favorited'] if 'total_favorited' in data['author'] else '未知'
    aweme_count = data['author']['aweme_count'] if 'aweme_count' in data['author'] else '未知'
    user_id = data['author']['unique_id'] if 'unique_id' in data['author'] else '未知'
    user_age = data['author']['user_age'] if 'user_age' in data['author'] else '未知'
    gender = data['author']['gender'] if 'gender' in data['author'] else '未知'
    if gender == 1:
        gender = '男'
    elif gender == 0:
        gender = '女'
    else:
        gender = '未知'
    try:
        ip_location = data['user']['ip_location']
    except:
        ip_location = '未知'
    aweme_id = data['aweme_id']
    nickname = data['author']['nickname']
    author_avatar = data['author']['avatar_thumb']['url_list'][0]
    video_cover = data['video']['cover']['url_list'][0]
    title = data['desc']
    desc = data['desc']
    admire_count = data['statistics']['admire_count'] if 'admire_count' in data['statistics'] else 0
    digg_count = data['statistics']['digg_count']
    commnet_count = data['statistics']['comment_count']
    collect_count = data['statistics']['collect_count']
    share_count = data['statistics']['share_count']
    video_addr = data['video']['play_addr']['url_list'][0]
    images = data['images']
    if not isinstance(images, list):
        images = []
    create_time = data['create_time']

    text_extra = data['text_extra'] if 'text_extra' in data else []
    text_extra = text_extra if text_extra else []
    topics = []
    for item in text_extra:
        hashtag_name = item['hashtag_name'] if 'hashtag_name' in item else ''
        if hashtag_name:
            topics.append(hashtag_name)

    work_type = '未知'
    if 'aweme_type' in data:
        if data['aweme_type'] == 68:
            work_type = '图集'
        elif data['aweme_type'] == 0:
            work_type = '视频'

    return {
        'work_id': aweme_id,
        'work_url': f'https://www.douyin.com/video/{aweme_id}',
        'work_type': work_type,
        'title': title,
        'desc': desc,
        'admire_count': admire_count,
        'digg_count': digg_count,
        'comment_count': commnet_count,
        'collect_count': collect_count,
        'share_count': share_count,
        'video_addr': video_addr,
        'images': images,
        'topics': topics,
        'create_time': create_time,
        'video_cover': video_cover,
        'user_url': user_url,
        'user_id': user_id,
        'nickname': nickname,
        'author_avatar': author_avatar,
        'user_desc': user_desc,
        'following_count': following_count,
        'follower_count': follower_count,
        'total_favorited': total_favorited,
        'aweme_count': aweme_count,
        'user_age': user_age,
        'gender': gender,
        'ip_location': ip_location
    }


def trim_search_work_info(work_info):
    return {k: v for k, v in work_info.items() if k not in SEARCH_EXCLUDED_FIELDS}


def save_to_xlsx(datas, file_path):
    if not datas:
        datas = [{}]
    wb = openpyxl.Workbook()
    ws = wb.active
    field_order = list(datas[0].keys())
    headers = [FIELD_LABELS.get(field, field) for field in field_order]
    ws.append(headers)
    for data in datas:
        row = [norm_text(str(data.get(field, ''))) for field in field_order]
        ws.append(row)
    wb.save(file_path)
    logger.info(f'数据保存至 {file_path}')

def download_media(path, name, url, type):
    if type == 'image':
        content = requests.get(url).content
        with open(path + '/' + name + '.jpg', mode="wb") as f:
            f.write(content)
    elif type == 'video':
        res = requests.get(url, stream=True)
        size = 0
        chunk_size = 1024 * 1024
        with open(path + '/' + name + '.mp4', mode="wb") as f:
            for data in res.iter_content(chunk_size=chunk_size):
                f.write(data)
                size += len(data)


def save_wrok_detail(work, path):
    with open(f'{path}/detail.txt', mode="w", encoding="utf-8") as f:
        for key, value in work.items():
            label = FIELD_LABELS.get(key, key)
            if key == 'images' and isinstance(value, list):
                value = ', '.join(value)
            elif key == 'topics' and isinstance(value, list):
                value = ', '.join(value)
            elif key == 'create_time':
                value = timestamp_to_str(value)
            f.write(f"{label}: {value}\n")


@retry(tries=3, delay=1)
def download_work(work_info, path, save_choice, save_payload=None):
    work_id = work_info['work_id']
    user_id = work_info['user_id']
    title = work_info['title']
    title = norm_str(title)[:40]
    nickname = work_info['nickname']
    nickname = norm_str(nickname)[:20]
    if title.strip() == '':
        title = f'无标题'
    save_path = f'{path}/{nickname}_{user_id}/{title}_{work_id}'
    check_and_create_path(save_path)
    if save_payload is None:
        save_payload = work_info
    with open(f'{save_path}/info.json', mode='w', encoding='utf-8') as f:
        f.write(json.dumps(save_payload, ensure_ascii=False) + '\n')
    work_type = work_info['work_type']
    save_wrok_detail(save_payload, save_path)
    if work_type == '图集' and save_choice in ['media', 'media-image', 'all']:
        for img_index, img_url in enumerate(work_info['images']):
            download_media(save_path, f'image_{img_index}', img_url, 'image')
    elif work_type == '视频' and save_choice in ['media', 'media-video', 'all']:
        download_media(save_path, 'cover', work_info['video_cover'], 'image')
        download_media(save_path, 'video', work_info['video_addr'], 'video')
    logger.info(f'作品 {work_info["work_id"]} 下载完成，保存路径: {save_path}')
    return save_path



def check_and_create_path(path):
    if not os.path.exists(path):
        os.makedirs(path)
