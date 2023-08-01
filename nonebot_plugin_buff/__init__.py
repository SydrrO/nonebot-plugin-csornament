from nonebot.plugin import PluginMetadata
from .config import Config
__plugin_meta__ = PluginMetadata(
    name="nonebot-plugin-buff",
    description="一款模拟buff查找饰品价格的机器人",
    usage="输入 查询/搜索/查 xxx 按照机器人的提示，将会获取到目前buff市场上最低的饰品价格",
    type="application",
    # 发布必填，当前有效类型有：`library`（为其他插件编写提供功能），`application`（向机器人用户提供功能）。
    homepage="https://github.com/Sydrr0/nonebot-plugin-buff",
    # 发布必填。
    config=Config,
    # 插件配置项类，如无需配置可不填写。
    supported_adapters={"~onebot.v11"},
    # 支持的适配器集合，其中 `~` 在此处代表前缀 `nonebot.adapters.`，其余适配器亦按此格式填写。
    # 若插件可以保证兼容所有适配器（即仅使用基本适配器功能）可不填写，否则应该列出插件支持的适配器。
)


# 插件初始化
from nonebot import get_driver
from .config import Config
global_config = get_driver().config
config = Config.parse_obj(global_config)

# nonebot2 的函数导入
from nonebot.matcher import Matcher
from nonebot.plugin import on_command
from nonebot.params import ArgPlainText # 提取消息内的字符串的方法
from nonebot.adapters import Message
from nonebot.params import CommandArg 
from nonebot.typing import T_State   # 继承上一个函数的方法
from nonebot import get_bot



# 后端爬虫所需要的插件
import httpx
import re
import os
from bs4 import BeautifulSoup

# 创建本地文件夹，用于存放数据
save_path = "./search_data"
if not os.path.exists(save_path):
    os.mkdir(save_path)
else:
    pass

search = on_command("查询", aliases={"搜索", "查"}, priority=10, block=True)

def find_numbers(keyword):
    num_list = []
    ob_name_list = []
    with open('./search_data/data.txt', 'r',encoding='utf-8') as file:
        for line in file:
            if keyword in line:
                # 寻找第一个逗号的位置
                comma_index = line.index(',')
                # 提取逗号前面的内容，并转换为 str
                number = str(line[:comma_index].strip())
                num_list.append(number)
                # 提取逗号后面的内容，并转换为 str
                ob_name = str(line[comma_index + 1:].strip())
                ob_name_list.append(ob_name)
    # 这里得到了两个列表，第一个是buff序号列表，第二个是商品名称列表
    return num_list,ob_name_list

def sending_txt(name_index):   # 传入两个列表，第一个是符合的商品编码。第二个是名称
    name_result_list = []    # 得到一个用以下 for 循环的结果，需要逐行输出
    for index in range(0,len(name_index)):
        # 把每一行的内容加入到name_resulr_list里面
        name_result_list.append('%i: %s'% (index, name_index[index]))          
    # 用换行符把列表里面每一个元素 join 成一个对象
    result = '\n'.join(str(item) for item in name_result_list)
    # 去除最后一行的换行符
    result = result.rstrip('\n')
    return result

async def get_miniprice(num,obtype): # num是获取到的商品index, ob_type是指崭新出厂之类的
#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! ob_type 还未表达，需使用正则表达式提取 !!!!!
    base_url ='https://buff.163.com/goods/'
    extra_url = str(num)
    url = base_url + extra_url
    async with httpx.AsyncClient() as client: # 异步 httpx 为了防止事件卡死
        response = await client.get(url)
        page_url = response.text
        data_getten = BeautifulSoup(page_url, "lxml")
        mini_price_html = str(data_getten.find_all("div", class_="scope-btns"))

    pattern = r'{ob_type}.*?data\-price\="([^"]+)"'.format(ob_type = obtype) 
    # 上面的正则表达式表示 ob_type 后面的第一个 data-price='' 中的值
    match = re.search(pattern, mini_price_html)
    if match:
        return match.group(1) # 查找第一个符合的值
    else:
        return None




@search.handle()  # 这是为了接收 查询xxx 中的xxx
async def handle_function(matcher: Matcher, args: Message = CommandArg()):
    if args.extract_plain_text():
        matcher.set_arg("name", args)  # 获取的xxx
    
@search.got("name", prompt="请输入饰品名称")
async def got_name(state: T_State, name: str = ArgPlainText()):
    name_input = f"{name}"  # 用户输入的饰品名称
    num_list = find_numbers(name_input)[0]  # 获取序号的列表
    obname_list = find_numbers(name_input)[1]  # 获取物品名称的列表
    asking_txt = sending_txt(name_index=obname_list)
    state['num_list'] = num_list  # 保存list到下一个函数内使用
    state['name_list'] = obname_list
    
    if not num_list and not obname_list:
        await search.finish('数据库中暂时未收录该饰品')
    else:
        await search.send(asking_txt)

# 正则表达式获取最后一个括号内的内容，就是obtype

@search.got("num_index", prompt="请输入序号")
async def got_num(state: T_State, num_index: str = ArgPlainText()):
    num_input = f"{num_index}"  # 用户输入的序号
    obindex = state['num_list'][int(num_input)]
    obname_full = state['name_list'][int(num_input)]
    pattern = r"\((.*?)\)[^()]*$"
    match = re.search(pattern, obname_full)
    if match:
        obname_type = match.group(1)
    else:
        pass

    miniprice = await get_miniprice(num=obindex, obtype=obname_type)
    await search.finish('%s\n现价: ￥ %s\nBuff代码: %s' % (obname_full, miniprice, obindex))
