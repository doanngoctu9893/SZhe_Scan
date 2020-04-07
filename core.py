from changanya.simhash import Simhash
import requests

def is_similar_page(res1, res2, radio=0.85):
    '''
    计算页面相似度函数
    :param res1:
    :param res2:
    :param radio:
    :return:
    '''
    if res1 is None or res2 is None:
        return False
    body1 = res1.text
    body2 = res2.text

    simhash1 = Simhash(body1)
    simhash2 = Simhash(body2)

    calc_radio = simhash1.similarity(simhash2)
    # print("[%s]与[%s]两个页面的相似度为:%s" % (url1, url2, calc_radio))
    if calc_radio >= radio:
        return True
    else:
        return False
'''
if 响应码 == 404:
    return this_is_404_page
elif 目标网页内容 与 网站404页面内容 相似：
    return this_is_404_page
else:
    return this_is_not_404_page
'''
def is_404(true_404,check_url):
    '''
    检测页面是否为404
        1,从状态码是否为404判断
        2,获取域名的404页面，然后判断请求的页面和404页面是否相似，相似则可以判断为404页面。
    当check_url为404页面时，返回true，否则返回false
    传入的参数为(真实的404界面，需要检测的url)，是能直接访问的url，形如http://xxx/xxx.html 非域名
    参考链接：
        https://xz.aliyun.com/t/4404
        https://thief.one/2018/04/12/1/
    :return:
    '''
    check_url_rep=requests.get(true_404)
    if check_url_rep.status_code==404:
        return True
    else:
        true_404_rep=requests.get(check_url)
        if is_similar_page(true_404_rep,check_url_rep):
            return True
        else:
            return False

#测试数据
# print(is_404("https://www.baidu.com/search/error.html","https://www.baidu.com/xxxxxxxxxxxxxxxxxxxxxxxxxxxx"))