import requests 
import pandas as pd


def get_event_data(event_id):
    url = 'https://api.fightinsider.io/gql'

    headers = {
        'authority': 'api.fightinsider.io',
        'accept': '*/*',
        'accept-language': 'en-US,en;q=0.9',
        # Already added when you pass json=
        # 'content-type': 'application/json',
        'origin': 'https://fightodds.io',
        'referer': 'https://fightodds.io/',
        'sec-ch-ua': '"Chromium";v="104", " Not A;Brand";v="99", "Google Chrome";v="104"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'cross-site',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36',
    }

    json_data = {
        'query': 'query EventOddsQuery(\n  $eventPk: Int!\n) {\n  sportsbooks: allSportsbooks(hasOdds: true) {\n    ...EventTabPanelOdds_sportsbooks\n  }\n  eventOfferTable(pk: $eventPk) {\n    slug\n    ...EventTabPanelOdds_eventOfferTable\n    id\n  }\n}\n\nfragment EventOfferTable_eventOfferTable on EventOfferTableNode {\n  name\n  pk\n  fightOffers {\n    edges {\n      node {\n        id\n        fighter1 {\n          firstName\n          lastName\n          slug\n          id\n        }\n        fighter2 {\n          firstName\n          lastName\n          slug\n          id\n        }\n        bestOdds1\n        bestOdds2\n        slug\n        propCount\n        isCancelled\n        straightOffers {\n          edges {\n            node {\n              sportsbook {\n                id\n                shortName\n                slug\n              }\n              outcome1 {\n                id\n                odds\n                ...OddsWithArrowButton_outcome\n              }\n              outcome2 {\n                id\n                odds\n                ...OddsWithArrowButton_outcome\n              }\n              id\n            }\n          }\n        }\n      }\n    }\n  }\n}\n\nfragment EventOfferTable_sportsbooks on SportsbookNodeConnection {\n  edges {\n    node {\n      id\n      shortName\n      slug\n    }\n  }\n}\n\nfragment EventTabPanelOdds_eventOfferTable on EventOfferTableNode {\n  fightOffers {\n    edges {\n      node {\n        id\n        isCancelled\n      }\n    }\n  }\n  ...EventOfferTable_eventOfferTable\n}\n\nfragment EventTabPanelOdds_sportsbooks on SportsbookNodeConnection {\n  ...EventOfferTable_sportsbooks\n}\n\nfragment OddsWithArrowButton_outcome on OutcomeNode {\n  id\n  ...OddsWithArrow_outcome\n}\n\nfragment OddsWithArrow_outcome on OutcomeNode {\n  odds\n  oddsPrev\n}\n',
        'variables': {
            'eventPk': event_id,
        },
    }

    response = requests.post(url, headers=headers, json=json_data)

    return response.json()


def get_win_odds(df):
    f1_list = []
    f2_list = []

    for edge in df['straightOffers.edges']:
        for node in edge:
            if(node['node']['sportsbook']['shortName'] == '5Dimes'):
                try:
                    f1_list.append(node['node']['outcome1']['odds'])
                except:
                    f1_list.append(None)
                try:
                    f2_list.append(node['node']['outcome2']['odds'])
                except:
                    f2_list.append(None)
                break        

    return(df.assign(f1_odds=f1_list,
                     f2_odds=f2_list))


def get_odds(ser, books_df, book):
    book_id = books_df.loc[books_df['node.shortName']==book,'node.id'].values[0]

    odds_list = []

    for edge in ser:
        odds = None
        for node in edge:
            if (node['node']['sportsbook']['id'] == book_id):
                try:
                    odds = node['node']['outcome1']['odds']
                except:
                    odds = None
                break
        odds_list.append(odds)

    return(pd.Series(odds_list))


def build_names_df(event_data):
    return (pd.json_normalize(event_data['data']['eventOfferTable']['fightOffers']['edges'])
                .rename(columns=lambda col: col.removeprefix('node.'))
                .query('isCancelled==False')
                .drop(columns=['id', 'isCancelled', 'fighter1.slug', 'fighter1.id', 'fighter2.slug', 'fighter2.id', 'bestOdds1', 'bestOdds2', 'propCount'])
                .pipe(get_win_odds)
            )


def build_odds_df(names_df):
    return (pd.concat([(names_df
                            [['fighter1.firstName', 'fighter1.lastName', 'f1_odds']]
                            .rename(columns={'fighter1.firstName':'first_name', 'fighter1.lastName':'last_name', 'f1_odds':'win_odds'})
                        ),(names_df
                            [['fighter2.firstName', 'fighter2.lastName', 'f2_odds']]
                            .rename(columns={'fighter2.firstName':'first_name', 'fighter2.lastName':'last_name', 'f2_odds':'win_odds'})
                        )], ignore_index=True)
                        .assign(fighter=lambda df_: df_.first_name + ' ' + df_.last_name)
                        .astype({'win_odds':'Int16'})
                        .drop(columns=['first_name'])
                        [['fighter', 'last_name', 'win_odds']]
            )


def build_props_df(names_df):
    url = 'https://api.fightinsider.io/gql'

    props_df = pd.DataFrame()

    for fight in names_df['slug']:

        headers = {
            'authority': 'api.fightinsider.io',
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9',
            # Already added when you pass json=
            # 'content-type': 'application/json',
            'origin': 'https://fightodds.io',
            'referer': 'https://fightodds.io/',
            'sec-ch-ua': '"Chromium";v="104", " Not A;Brand";v="99", "Google Chrome";v="104"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'cross-site',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36',
        }

        json_data = {
            'query': 'query FightPropOfferTableQrQuery(\n  $fightSlug: String!\n) {\n  sportsbooks: allSportsbooks(hasOdds: true) {\n    ...FightPropOfferTable_sportsbooks\n  }\n  fightPropOfferTable(slug: $fightSlug) {\n    ...FightPropOfferTable_fightPropOfferTable\n    id\n  }\n  offerTypes: allOfferTypes {\n    ...FightPropOfferTable_offerTypes\n  }\n}\n\nfragment FightPropOfferTable_fightPropOfferTable on FightPropOfferTableNode {\n  propOffers {\n    edges {\n      node {\n        propName1\n        propName2\n        bestOdds1\n        bestOdds2\n        offerType {\n          id\n        }\n        offers {\n          edges {\n            node {\n              sportsbook {\n                id\n              }\n              outcome1 {\n                id\n                odds\n                ...OddsWithArrowButton_outcome\n              }\n              outcome2 {\n                id\n                odds\n                ...OddsWithArrowButton_outcome\n              }\n              id\n            }\n          }\n        }\n      }\n    }\n  }\n}\n\nfragment FightPropOfferTable_offerTypes on OfferTypeNodeConnection {\n  edges {\n    node {\n      id\n    }\n  }\n}\n\nfragment FightPropOfferTable_sportsbooks on SportsbookNodeConnection {\n  edges {\n    node {\n      id\n      shortName\n      slug\n    }\n  }\n}\n\nfragment OddsWithArrowButton_outcome on OutcomeNode {\n  id\n  ...OddsWithArrow_outcome\n}\n\nfragment OddsWithArrow_outcome on OutcomeNode {\n  odds\n  oddsPrev\n}\n',
            'variables': {
                'fightSlug': f'{fight}',
            },
        }

        r = requests.post(url, headers=headers, json=json_data)

        data = r.json()
        props = data['data']['fightPropOfferTable']['propOffers']['edges'][1:]
        
        props_df = pd.concat([props_df, pd.json_normalize(props)], ignore_index=True)

    return props_df


def clean_props_df(props_df, books_df):
    terms = ['wins inside distance',
         'wins by decision',
         'wins in round 1',
         'wins in round 2',
         'wins in round 3',
         'wins in round 4',
         'wins in round 5']

    pattern = '|'.join(terms)

    props_df = (props_df
                .assign(odds=get_odds(props_df['node.offers.edges'], books_df, '5Dimes').astype('Int16'))
                [['node.propName1', 'odds']]
                .rename(columns={'node.propName1':'prop'})
                .dropna()
                .reset_index(drop=True)
    )

    return (props_df
                .query('prop.str.contains(@pattern)')
                .assign(**props_df.prop.str.extract(r'(?P<last_name>.*) (?P<prop>wins.*)'))
                .astype({'odds':'float64'})
                .pivot_table(index='last_name', columns='prop', values='odds')
                .round(0)
                .astype('Int16')
                .fillna(0)
    )


def build_odds_table(odds_df, props_df):
    ordered_cols = ['fighter', 'win', 'itd', 'dec', 'r1', 'r2', 'r3', 'r4', 'r5']

    return (pd.merge(odds_df, props_df, how='left', on='last_name')
                .drop(columns=['last_name'])
                .rename(columns={'win_odds':'win',
                                'wins inside distance':'itd',
                                'wins by decision':'dec',
                                'wins in round 1':'r1',
                                'wins in round 2':'r2',
                                'wins in round 3':'r3',
                                'wins in round 4':'r4',
                                'wins in round 5':'r5'})
                [ordered_cols]
            )


if __name__ == '__main__':
    # event_id = input('Enter event id: ')
    event_id = '4556'

    event_data = get_event_data(event_id)
    books_df = pd.json_normalize(event_data['data']['sportsbooks']['edges'])
    names_df = build_names_df(event_data)
    odds_df = build_odds_df(names_df)
    props_df = build_props_df(names_df)
    props_df = clean_props_df(props_df, books_df)
    odds_table = build_odds_table(odds_df, props_df)

    # folder = input('Enter folder name: ')
    folder = 'UFC 287//'
    odds_table.to_csv('fightodds.csv', index=False)
    odds_table.to_csv(folder + 'odds.csv', index=False)