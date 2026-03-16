项目地址：https://github.com/cv-cat/DouYin_Spider

python cli.py --help
python cli.py search --help
最重要的搜索功能，推荐先这样跑，只导出 Excel，不下载媒体：

python cli.py search "榴莲" --num 20 --save-choice excel --excel-name durian_20
按点赞排序搜 50 条视频：

python cli.py search "榴莲" --num 50 --save-choice excel --excel-name durian_top50 --sort-type 1 --content-type 1
搜索并下载媒体：

python cli.py search "榴莲" --num 20 --save-choice all --excel-name durian_all
抓用户全部作品，传主页链接或直接传 sec_user_id 都行：

python cli.py user "https://www.douyin.com/user/MS4wLjABAAAAULqT-SrJDT7RqeoxeGg1hB14Ia5UI9Pm66kzKmI1ITD2Fo3bUhqYePBaztkzj7U5" --save-choice excel --excel-name user_works
python cli.py user "MS4wLjABAAAAULqT-SrJDT7RqeoxeGg1hB14Ia5UI9Pm66kzKmI1ITD2Fo3bUhqYePBaztkzj7U5" --save-choice all
抓单个或多个作品：

python cli.py work "https://www.douyin.com/video/7445533736877264178" --save-choice excel --excel-name single_work
python cli.py work "URL1" "URL2" --save-choice all --excel-name batch_works
监听直播：

python cli.py live "81804234251"