from scrapecard import GetCardInfo

urls = ['http://ufcstats.com/event-details/d1e7fc58d4225cdf'
        ]

for url in urls:
    GetCardInfo(url)