import requests
from bs4 import BeautifulSoup

import networkx as nx
import matplotlib.pyplot as plt

test_urls = [
    'https://en.wikipedia.org/wiki/Alex_Jones',
    'https://en.wikipedia.org/wiki/James_H._Fetzer',
]

no_link = [
    '/wiki/ISSN_(identifier)',
    '/wiki/ISNI_(identifier)',
    '/wiki/VIAF_(identifier)',
    '/wiki/Help:Category',
    '/wiki/Category:Web_scraping',
    '/wiki/Category:CS1_Danish-language_sources_(da)',
    '/wiki/Category:CS1_French-language_sources_(fr)',
    '/wiki/Category:Articles_with_short_description',
    '/wiki/Category:Short_description_matches_Wikidata',
    '/wiki/Category:Articles_needing_additional_references_from_June_2017',
    '/wiki/Category:All_articles_needing_additional_references',
    '/wiki/Category:Articles_needing_additional_references_from_October_2018',
    '/wiki/Category:Articles_with_limited_geographic_scope_from_October_2015',
    '/wiki/Category:United_States-centric',
]

def get_links(url):
    soup = BeautifulSoup(requests.get(url).content, 'html.parser')

    wlinks = []
    for link in soup.find(id='bodyContent').find_all('a'):
        try:
            if link['href'].find('/wiki/') != -1 \
                    and link['href'].find('/wiki/File') == -1 \
                    and ':' not in link['href'] \
                    and link['href'] not in no_link:
                wlinks.append(link['href'])
        except:
            pass 
    return wlinks

def draw_graph(start_nodes=['/wiki/Alex_Jones','/wiki/James_H._Fetzer']):
    all_links = list(map(lambda x:get_links('https://en.wikipedia.org'+x),start_nodes))
    linkset = set(start_nodes+all_links[0]+all_links[1])
    link2id = dict(zip(linkset,range(len(linkset))))
    id2link = dict(zip(link2id.values(), link2id.keys()))
    
    all_edges = [e for i in range(len(start_nodes)) for e in list(map(lambda x:(link2id[start_nodes[i]],link2id[x]),set(all_links[i])))]
    
    G = nx.Graph()
    G.add_nodes_from(id2link.keys())
    G.add_edges_from(all_edges)
    nx.draw(G,labels=dict(map(lambda x:(link2id[x],x),start_nodes)),with_labels=True)
    plt.show()
    print('done')

    
# url = 'https://en.wikipedia.org/wiki/Web_scraping'
# print(get_links(url))
# print()
# 
# url = 'https://en.wikipedia.org/wiki/Southwest_Airlines'
# print(get_links(url))
# 
# print(set(get_links('https://en.wikipedia.org/wiki/Web_scraping')).intersection(
# set(get_links('https://en.wikipedia.org/wiki/Southwest_Airlines'))
# ))

def get_references(url):
    soup = BeautifulSoup(requests.get(url).content, 'html.parser')

    wlinks = []
    for link in soup.find(id='bodyContent').find_all('a'):
        try:
            if link['href'].find('/wiki/') != -1 \
                    and link['href'].find('/wiki/File') == -1 \
                    and ':' not in link['href'] \
                    and link['href'] not in no_link:
                children = list(link.children)
                if link.content is not None:
                    print('CONTENT:')
                    print(link.content)
                    print('_________________________________________________________________')

                if len(children) != 1 or not isinstance(children[0],str):
                    print(len(children) != 1, not isinstance(children[0],str))
                    print(link)
                    print(children)
                    # print(dir(children[0]))
                    print(children[0].text)
                    print(soup.find(id='bodyContent').find_all(children[0].text))
                    print('------------------------------------------------------------------')
                else:
                    print(children[0])
                    print(children[0].text)
                    print(soup.find_all(children[0]))
                    break
                # print('------------------------------------------------------------------')
                wlinks.append(link['href'])
        except:
            pass 
    exit()
    return wlinks

def main():

    from bs4.element import Comment

    def tag_visible(element):
        if element.parent.name in ['style', 'script', 'head', 'title', 'meta', '[document]']:
            return False
        if isinstance(element, Comment):
            return False
        return True
    
    
    def text_from_html(url):
        soup = BeautifulSoup(requests.get(url).content, 'html.parser')
        texts = soup.find_all(text=True)
        visible_texts = filter(tag_visible, texts)
        return u" ".join(t.strip() for t in visible_texts)

    print(text_from_html('https://en.wikipedia.org/wiki/Web_scraping'))
    # draw_graph()
    # print(get_references('https://en.wikipedia.org/wiki/Web_scraping'))

if __name__=='__main__':main()

