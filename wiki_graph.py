import re
import requests

from bs4 import BeautifulSoup
from bs4.element import Comment

from edge_classifier import EdgeClassifier

import networkx as nx

from urllib.parse import unquote

import matplotlib.pyplot as plt

from random import sample

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

class context_graph:
    def __init__(self,neo=False):
        self.neo = neo
        if neo:
            import nxneo4j as nxn
            from neo4j import GraphDatabase
            driver = GraphDatabase.driver(uri="bolt://localhost:7687")

            self.G = nxn.Graph(driver)
            self.G.delete_all()
        else:
            self.G = nx.Graph()

        self.docs = dict()
        self.ec = EdgeClassifier()

    def get_graph(self):
        return self.G

    def get_links_and_text(self,url,**kwargs):
        url = 'https://en.wikipedia.org'+url
        soup = BeautifulSoup(requests.get(url).content, 'html.parser')
    
        links = dict()
        for link in soup.find(id='bodyContent').find_all('a'):
            try:
                if link['href'].find('/wiki/') != -1 \
                        and link['href'].find('/wiki/File') == -1 \
                        and ':' not in link['href'] \
                        and link['href'] not in no_link:
                    children = list(link.children)
                    if len(children) == 1 and isinstance(children[0],str):
                        links[link['href']] = children[0].text
            except:
                pass
    
        return links

    def wiki_get_node_text(self,url,docid):
        url = 'https://en.wikipedia.org'+url
        soup = BeautifulSoup(requests.get(url).content, 'html.parser')

        texts = soup.find_all(text=True)
        visible_texts = filter(tag_visible, texts)
        self.docs[docid] = ' '.join(t.strip() for t in visible_texts if t not in ['','\n','\t'])

    
    def get_edge_weight(self,docid,text):
        all_text = self.docs[docid]
        intro = all_text[:all_text.index('Contents')]
        intro = '. '.join(list(filter(lambda x:x,intro.split('. ')))[-2:])
    
        text_window = get_window(all_text,text,120)
        if ' ' in text_window:
            text_window = text_window[text_window.index(' ')+1:text_window.rindex(' ')]
            if text_window != '':
                return float(self.ec.compare(intro,text_window))
        return -1
    
    def __call__(self,url,n=5,max_iter=5,max_pc=1000):
        central_nodes = set()
        node_counts = [0]
        edges = dict()
        link2id = {url:0}
        id2link = [url]
    
        central_nodes.add(link2id[url])
        links = self.get_links_and_text(url)
        for l,t in links.items():
            if l not in id2link:
                link2id[l] = len(id2link)
                id2link.append(l)
                node_counts.append(0)
            if url != l:
                node_counts[link2id[l]] += 1
                # edges[frozenset({link2id[url],link2id[l]})] = (url,t)
                edges[frozenset({link2id[url],link2id[l]})] = (link2id[url],t)
    
        for url in list(filter(lambda x:x not in central_nodes,sample(links.keys(),n)))[:n-1]:
            central_nodes.add(link2id[url])
            links = self.get_links_and_text(url,skip=True)
            for l,t in links.items():
                if l not in id2link:
                    link2id[l] = len(id2link)
                    id2link.append(l)
                    node_counts.append(0)
                if url != l:
                    node_counts[link2id[l]] += 1
                    # edges[frozenset({link2id[url],link2id[l]})] = (url,t)
                    edges[frozenset({link2id[url],link2id[l]})] = (link2id[url],t)
    
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
                links = self.get_links_and_text(url,skip=True)
                for l,t in links.items():
                    if l in id2link and url != l:
                        node_counts[link2id[l]] += 1
                        # edges[frozenset({link2id[url],link2id[l]})] = (url,t)
                        edges[frozenset({link2id[url],link2id[l]})] = (link2id[url],t)
                pbar.update(1)
    
        # in_edges = list(filter(lambda x:x[2]['weight'] >= 0 and not {x[0],x[1]}-central_nodes,map(lambda y:tuple(list(y[0])+[{'weight':wiki_get_edge_weight(*y[1],ec=ec)}]),edges.items())))
    
        print(''.join(['-']*50))
        print('Creating Graph:',len(central_nodes)+len(edges))
        pbar = tqdm(total=len(central_nodes)+len(edges))
    
        for nid in central_nodes:
            self.wiki_get_node_text(id2link[nid],nid)
            name = unquote(id2link[nid].split('/')[-1])
            self.G.add_node(name,nid=nid)
            pbar.update(1)
        for (a,b),(u,t) in list(edges.items()):
            if {a,b}-central_nodes:
                w = self.get_edge_weight(u,t)
                if w >= 0:
                    name0 = unquote(id2link[a].split('/')[-1])
                    name1 = unquote(id2link[b].split('/')[-1])
                    self.G.add_edge(name0,name1,weight=w)
            pbar.update(1)
        if not self.neo:
            nx.draw(self.G,with_labels=True)
            plt.show()
    
def main():
    # G = generate_context_graph('/wiki/Nelly_Martyl',n=2,max_iter=1,max_pc=1,neo=True)
    # G = generate_context_graph('/wiki/Nelly_Martyl',n=5,max_iter=2,max_pc=15,neo=True)
    CG = context_graph(False)
    CG('/wiki/Alex_Jones',n=5,max_iter=2,max_pc=5)

if __name__=='__main__' : main()

