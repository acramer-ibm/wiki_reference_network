import re
import requests

from bs4 import BeautifulSoup
from bs4.element import Comment

from edge_classifier import EdgeClassifier

import networkx as nx
import nxneo4j as nxn
from neo4j import GraphDatabase

from urllib.parse import unquote

import matplotlib.pyplot as plt

from random import choice as random_choice, choices as random_choices

from tqdm import tqdm

no_link = [
    '/wiki/JSTOR_(identifier)',
    '/wiki/MBA_(identifier)',
    '/wiki/Trove_(identifier)',
    '/wiki/Doi_(identifier)',
    '/wiki/ISBN_(identifier)',
    '/wiki/SUDOC_(identifier)',
    '/wiki/OCLC_(identifier)',
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

def wiki_get_links(url):
    return get_links('https://en.wikipedia.org'+url)

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
    all_links = list(map(wiki_get_links,start_nodes))
    linkset = set(start_nodes+all_links[0]+all_links[1])
    # linkset = set(start_nodes+[l for ls in all_links for l in ls])
    link2id = dict(zip(linkset,range(len(linkset))))
    id2link = dict(zip(link2id.values(), link2id.keys()))
    # id2link = list(linkset)
    # link2id = dict(zip(id2link,range(len(id2link))))

    all_edges = [e for i in range(len(start_nodes)) for e in list(map(lambda x:(link2id[start_nodes[i]],link2id[x]),set(all_links[i])))]

    G = nx.Graph()
    G.add_nodes_from(id2link.keys())
    G.add_edges_from(all_edges)
    nx.draw(G,labels=dict(map(lambda x:(link2id[x],x),start_nodes)),with_labels=True)
    plt.show()
    print('done')

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
                    pass
                    # print(children[0])
                    # print(children[0].text)
                    # print(soup.find_all(children[0]))
                    # break
                # print('------------------------------------------------------------------')
                # wlinks.append(link['href'].children[0].text)
                wlinks.append(children[0].text)
        except:
            pass
    return wlinks

def tag_visible(element):
    if element.parent.name in ['h1','style', 'script', 'head', 'title', 'meta', '[document]']:
        return False
    if isinstance(element, Comment):
        return False
    if element in ['','\n','\t']:
        return False
    if len(element.findParents('table')):
        return False
    return True

def text_from_html(url):
    soup = BeautifulSoup(requests.get(url).content, 'html.parser')
    texts = soup.find_all(text=True)
    visible_texts = filter(tag_visible, texts)
    return ' '.join(t.strip() for t in visible_texts if t not in ['','\n','\t'])

def get_window(doc, ref, window_size=30):
    search = re.search(r'\b('+ref+r')\b', doc)
    if search:
        return doc[max(search.start()-window_size,0):(search.end()+window_size)]
    return ''


def generate_graph(url,n=5,max_iter=5,max_pc=1000):
    central_nodes = set()
    node_counts = [0]
    edges = set()
    link2id = {url:0}
    id2link = [url]

    # for _ in range(n):
    #     print(''.join(['-']*50))
    #     central_nodes.add(link2id[url])
    #     print('Central Nodes:',*list(map(lambda x:id2link[x][6:],central_nodes)))
    #     links = set(wiki_get_links(url))
    #     print('Num Links:',len(links))
    #     for l in links:
    #         if l not in id2link:
    #             link2id[l] = len(id2link)
    #             id2link.append(l)
    #             node_counts.append(0)
    #         if url != l:
    #             node_counts[link2id[l]] += 1
    #             edges.add(frozenset({link2id[url],link2id[l]}))

    #     # new_nodes = list(set(links).difference(central_nodes))
    #     new_nodes = list(set(links).difference(map(lambda x:id2link[x],central_nodes)))
    #     print('Num new links:',len(new_nodes))
    #     print('Node Counts:',len(node_counts))
    #     url = random_choice(new_nodes)

    print(''.join(['-']*50))
    central_nodes.add(link2id[url])
    print('Central Nodes:',*list(map(lambda x:id2link[x][6:],central_nodes)))
    links = set(wiki_get_links(url))
    print('Num Links:',len(links))
    for l in links:
        if l not in id2link:
            link2id[l] = len(id2link)
            id2link.append(l)
            node_counts.append(0)
        if url != l:
            node_counts[link2id[l]] += 1
            edges.add(frozenset({link2id[url],link2id[l]}))

    new_nodes = list(set(links).difference(map(lambda x:id2link[x],central_nodes)))
    print('Num new links:',len(new_nodes))
    print('Node Counts:',len(node_counts))

    for url in random_choices(new_nodes,k=(n-1)):
        print(''.join(['-']*50))
        central_nodes.add(link2id[url])
        print('Central Nodes:',*list(map(lambda x:id2link[x][6:],central_nodes)))
        links = set(wiki_get_links(url))
        print('Num Links:',len(links))
        for l in links:
            if l not in id2link:
                link2id[l] = len(id2link)
                id2link.append(l)
                node_counts.append(0)
            if url != l:
                node_counts[link2id[l]] += 1
                edges.add(frozenset({link2id[url],link2id[l]}))

    print()
    print()

    for _ in range(max_iter):
        precentral = list(map(lambda y:y[0],
                       filter(lambda x:x[1]>1 and x[0] not in central_nodes,
                       enumerate(node_counts))))[:max_pc]
        print(''.join(['-']*50))
        print('Precentral:',len(precentral))
        if not precentral: break

        pbar = tqdm(total=len(precentral))

        for lid in precentral:
            url = id2link[lid]
            central_nodes.add(lid)
            links = set(wiki_get_links(url))
            for l in links:
                if l in id2link and url != l:
                    node_counts[link2id[l]] += 1
                    edges.add(frozenset({link2id[url],link2id[l]}))
            pbar.update(1)
    in_edges = set(filter(lambda x:not x-central_nodes,edges))

    G = nx.Graph()
    G.add_nodes_from(central_nodes)
    G.add_edges_from(in_edges)
    print(*list(map(lambda n:'{:04d} - {}'.format(n,unquote(id2link[n].split('/')[-1])),sorted(G.nodes))),sep='\n')
    # nx.draw(G,labels=dict(map(lambda x:(x,id2link[x][6:]),central_nodes)),with_labels=True)
    nx.draw(G,with_labels=True)
    plt.show()
    return G

def wiki_get_classified_links(url,ec):
    return get_classified_links('https://en.wikipedia.org'+url,ec)

def get_classified_links(url,ec):
    soup = BeautifulSoup(requests.get(url).content, 'html.parser')

    links_and_text = []   
    for link in soup.find(id='bodyContent').find_all('a'):
        try:
            if link['href'].find('/wiki/') != -1 \
                    and link['href'].find('/wiki/File') == -1 \
                    and ':' not in link['href'] \
                    and link['href'] not in no_link:
                children = list(link.children)
                if len(children) == 1 and isinstance(children[0],str):
                    links_and_text.append((link['href'],children[0].text))
        except:
            pass
    #TODO: ignore 'from wikipedia... this article... for.... refer to...'
    #TODO: ignore contents
    texts = soup.find_all(text=True)
    visible_texts = filter(tag_visible, texts)
    all_text = ' '.join(t.strip() for t in visible_texts if t not in ['','\n','\t'])
    intro = all_text[:all_text.index('Contents')]
    intro = '. '.join(list(filter(lambda x:x,intro.split('. ')))[-2:])

    links = dict()
    for link,text in links_and_text:
        text_window = get_window(all_text,text,120)
        text_window = text_window[text_window.index(' ')+1:text_window.rindex(' ')]
        if text_window != '':
            links[link] = ec.compare(intro,text_window)
    return links

def generate_context_graph(url,n=5,max_iter=5,max_pc=1000,neo=False):
    ec = EdgeClassifier()

    central_nodes = set()
    node_counts = [0]
    edges = dict()
    link2id = {url:0}
    id2link = [url]

    print(''.join(['-']*50))
    central_nodes.add(link2id[url])
    print('Central Nodes:',*list(map(lambda x:id2link[x][6:],central_nodes)))
    links = wiki_get_classified_links(url,ec)
    print('Num Links:',len(links))
    for l,w in links.items():
        if l not in id2link:
            link2id[l] = len(id2link)
            id2link.append(l)
            node_counts.append(0)
        if url != l:
            node_counts[link2id[l]] += 1
            edges[frozenset({link2id[url],link2id[l]})] = w

    new_nodes = list(set(links.keys()).difference(map(lambda x:id2link[x],central_nodes)))
    print('Num new links:',len(new_nodes))
    print('Node Counts:',len(node_counts))

    for url in random_choices(new_nodes,k=(n-1)):
        print(''.join(['-']*50))
        central_nodes.add(link2id[url])
        print('Central Nodes:',*list(map(lambda x:id2link[x][6:],central_nodes)))
        links = wiki_get_classified_links(url,ec)
        print('Num Links:',len(links))
        for l,w in links.items():
            if l not in id2link:
                link2id[l] = len(id2link)
                id2link.append(l)
                node_counts.append(0)
            if url != l:
                node_counts[link2id[l]] += 1
                edges[frozenset({link2id[url],link2id[l]})] = w

    print()
    print()

    for _ in range(max_iter):
        precentral = list(map(lambda y:y[0],
                       filter(lambda x:x[1]>1 and x[0] not in central_nodes,
                       enumerate(node_counts))))[:max_pc]
        print(''.join(['-']*50))
        print('Precentral:',len(precentral))
        if not precentral: break

        pbar = tqdm(total=len(precentral))

        for lid in precentral:
            url = id2link[lid]
            central_nodes.add(lid)
            links = wiki_get_classified_links(url,ec)
            for l in links:
                if l in id2link and url != l:
                    node_counts[link2id[l]] += 1
                    edges.add(frozenset({link2id[url],link2id[l]}))
            pbar.update(1)
    # in_edges = set(filter(lambda x:not x-central_nodes,edges))
    in_edges = set(filter(lambda x:not {x[0],x[1]}-central_nodes,map(lambda y:tuple(list(y[0])+[{'weight':y[1]}]),edges.items())))

    if neo:
        driver = GraphDatabase.driver(uri="bolt://localhost:7687")
        G = nxn.Graph(driver)
        G.delete_all()
    else:
        G = nx.Graph()

    # G.add_nodes_from(central_nodes)
    # G.add_edges_from(in_edges)
    for nid in central_nodes:
        name = unquote(id2link[n].split('/')[-1])
        G.add_node(name,nid=nid)
    for nid0,nid1,attrs in in_edges.items():
        G.add_edge(nid0,nid1,**attrs)
    if not neo:
        print(*list(map(lambda n:'{:04d} - {}'.format(n,unquote(id2link[n].split('/')[-1])),sorted(G.nodes))),sep='\n')
        nx.draw(G,with_labels=True)
        plt.show()

    return G


def main():

    # url = 'https://en.wikipedia.org/wiki/World_War_I'
    # soup = BeautifulSoup(requests.get(url).content, 'html.parser')
    # print(list(map(lambda x:x['href'],filter(lambda x:x['href'] == 'https://en.wikipedia.org/wiki/World_War_I',soup.find(id='bodyContent').find_all('link')))))
    # # soup = BeautifulSoup(requests.get(url).content, 'html.parser')
    # # print(list(map(lambda x:x['href'],filter(lambda x:x['rel'] == 'canonical',soup.find(id='bodyContent').find_all('link')))))
    # # print(url)
    # 
    # url = 'https://en.wikipedia.org/wiki/First_World_War'
    # soup = BeautifulSoup(requests.get(url).content, 'html.parser')
    # print(list(map(lambda x:x['href'],filter(lambda x:x['href'] == 'https://en.wikipedia.org/wiki/World_War_I',soup.find(id='bodyContent').find_all('link')))))
    # exit()

    # soup = BeautifulSoup(.content, 'html.parser')
    # print()

    # TEST URLS
    # url = 'https://en.wikipedia.org/wiki/Web_scraping'
    # url = 'https://en.wikipedia.org/wiki/Alex_Jones'
    # url = 'https://en.wikipedia.org/wiki/James_H._Fetzer'
    # print(generate_graph('/wiki/Alex_Jones',max_iter=1,max_pc=10))
    G = generate_context_graph('/wiki/Nelly_Martyl',max_iter=3,max_pc=20,neo=True)

    # print(get_window(text_from_html(url),'Sandy Hook Elementary School shooting',300))
    # print(get_references(url))
    # print(get_window(text_from_html(url),'From'))
    # print(get_window(text_from_html(url),'Austin',60))
    # print(get_window(text_from_html(url),'Sandy',120))

if __name__=='__main__' : main()

