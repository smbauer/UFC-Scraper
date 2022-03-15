from bs4 import BeautifulSoup
import requests
import sqlite3
from time import time

def GetFighterInfo(fighter):

    source = requests.get(fighter['link']).text

    soup = BeautifulSoup(source, 'lxml')

    fighterInfo = {}

    record = soup.select('.b-content__title-record')[0].text
    fighterInfo['record'] = record.split()[1]

    fighterInfo['nickname'] = soup.select('.b-content__Nickname')[0].text.strip()

    basicInfo = soup.find_all('li', class_='b-list__box-list-item')

    height = basicInfo[0].text.split()
    fighterInfo['height'] = ''.join(height[1:len(height)])

    weight = basicInfo[1].text.split()
    fighterInfo['weight'] = ' '.join(weight[1:len(weight)])

    reach = basicInfo[2].text.split()
    fighterInfo['reach'] = ''.join(reach[1:len(reach)])

    stance = basicInfo[3].text.split()
    fighterInfo['stance'] = ''.join(stance[1:len(stance)])

    dob = basicInfo[4].text.split()
    fighterInfo['dob'] = ' '.join(dob[1:len(dob)])

    cur.execute('''INSERT OR IGNORE INTO Fighter (name, nickname, height, reach, weight,
        stance, dob, record, link) VALUES ( ?, ?, ?, ?, ?, ?, ?, ?, ? )''', ( fighter['name'],
        fighterInfo['nickname'], fighterInfo['height'], fighterInfo['reach'], fighterInfo['weight'],
        fighterInfo['stance'], fighterInfo['dob'], fighterInfo['record'], fighter['link'] ) )

    cur.execute('SELECT id FROM Fighter WHERE link = ? ', (fighter['link'], ))
    fighter_id = cur.fetchone()[0]

    return fighter_id

#break up strikes, tds (x of y) into (landed,attempted)
def ParseStats(statsList):
    tempList = []

    #might be able to improve things with list comprehension or try/except
    for piece in statsList:
        if (piece == None) or (' of ' not in piece):
            tempList.append(piece)
        else:
            piece = piece.split(' of ')
            tempList.append(piece[0])
            tempList.append(piece[1])

    return tempList

###############################
## GetFightInfo()
## takes dictionary with preliminary info about the fight as input (event name,
## weightClass, fightNum, url)
## currently no return value
#################################
def GetFightInfo(fightInfo):

    source = requests.get(fightInfo['link']).text

    soup = BeautifulSoup(source, 'lxml')

    #select the section with the participant info
    person = soup.find_all('div', class_='b-fight-details__person')

    ######################
    # maybe create a class for fighter?
    #########################

    fighterA = {}
    fighterB = {}

    #parse the participant info to get the name, result and link to their page
    #### repetitive, feels like i can probably write some sort of loop for this part?
    #### can probably ditch the dictionaries and return values for these modules
    #### where i just insert everything into the db, maybe do a version where
    #### everything is written to a csv
    fighterA['result'] = person[0].i.text.strip()
    fighterA['name'] = person[0].a.text.strip()
    fighterA['link'] = person[0].a.get('href', None)

    fighterB['result'] = person[1].i.text.strip()
    fighterB['name'] = person[1].a.text.strip()
    fighterB['link'] = person[1].a.get('href', None)

    ############
    fighterA['id'] = GetFighterInfo(fighterA)
    fighterB['id'] = GetFighterInfo(fighterB)
    ############

    #figure out who the winner was
    if fighterA['result'] == 'W':
        fightInfo['winner'] = fighterA['id']
    elif fighterB['result'] == 'W':
        fightInfo['winner'] = fighterB['id']
    elif fighterA['result'] == 'D':
        fightInfo['winner'] = 1     #id for the Draw outcome
    else:
        fightInfo['winner'] = 2     #id for the No Contest outcome

    print('Fighter A:', fighterA['name'])
    print('Fighter B:', fighterB['name'])
    print('Winner ID:', fightInfo['winner'])

    #search the fight description to see if this is a title fight
    description = soup.select('.b-fight-details__fight-head')[0].text

    #figure out if it's a title fight
    if 'Title' in description:
        fightInfo['titleFight'] = 1
    else:
        fightInfo['titleFight'] = 0

    contentParts = soup.find_all('p', class_='b-fight-details__text')
    firstParts = contentParts[0].select('p > i')
    secondPart = contentParts[1].text.split()

    #get the fight ending method
    method = firstParts[0].text.split()
    fightInfo['method'] = ' '.join(method[1:len(method)])

    #get the final round of the fight
    rounds = firstParts[1].text.split()
    fightInfo['round'] = int(rounds[1])

    #get text value of time elapsed in final round
    ftime = firstParts[2].text.split()
    fightInfo['time'] = ftime[1]

    #convert to total time of fight (float)
    fmins = int(ftime[1].split(':')[0])
    fsecs = int(ftime[1].split(':')[1])

    if fmins == 5:
        total_time = fightInfo['round'] * fmins
    else:
        total_time = round((fightInfo['round'] - 1) * 5 + fmins + fsecs/60.0, 2)

    format = firstParts[3].text.split()
    fightInfo['format'] = ' '.join(format[1:len(format)])
    try:
        fightInfo['fightLength'] = int(format[2])
        print('rounds:', fightInfo['fightLength'])
        if fightInfo['fightLength'] < 3: return None
    except:
        fightInfo['fightLength'] = None     #no time limit
        print('no time limit...skipping')
        return None

    referee = firstParts[4].text.split()
    fightInfo['referee'] = ' '.join(referee[1:len(referee)])

    fightInfo['details'] = ' '.join(secondPart[1:len(secondPart)])

    #get all the tables with the fight stats
    tableList = soup.find_all('tbody')

    tempTables = []
    start = 0
    tableNum = 0

#    try:
    #clean up each of the tables
    for table in tableList:
        table = table.text.splitlines()
        for part in table:
            if part.strip() == '' : continue
            tempTables.append(part.strip())
        end = len(tempTables)
        tableList[tableNum] = tempTables[start:end]
        start = end
        tableNum += 1

    #separate into individual tables so it's easier to work with
    basicTable = tableList[0]       #basic stats summary
    basicRoundsTable = tableList[1] #basic stats by round
    ssTable = tableList[2]          #sig strikes breakdown
    ssRoundsTable = tableList[3]    #sig strikes breakdown by round

    #replace '---' and '--' with null values
    basicTable = [None if (x == '--' or x == '---') else x for x in basicTable]

    #split basicTable into stats for each fighter
    ####should turn this into a loop when i change fighterA/B into [0]/[1]
    fighterA['basicStatsFor'] = ParseStats(basicTable[2::2])
    fighterB['basicStatsFor'] = ParseStats(basicTable[3::2])

    fighterA['advStrStatsFor'] = ParseStats(ssTable[6::2])
    fighterB['advStrStatsFor'] = ParseStats(ssTable[7::2])

    #convert control time to an integer of total mins (easier for sql)
    try:
        a_ctrl_mins = int(fighterA['basicStatsFor'][11].split(':')[0])
        a_ctrl_secs = int(fighterA['basicStatsFor'][11].split(':')[1])
        fighterA['basicStatsFor'][11] = round(a_ctrl_mins + a_ctrl_secs/60.0,2)
    except:
        fighterA['basicStatsFor'][11] = 0

    try:
        b_ctrl_mins = int(fighterB['basicStatsFor'][11].split(':')[0])
        b_ctrl_secs = int(fighterB['basicStatsFor'][11].split(':')[1])
        fighterB['basicStatsFor'][11] = round(b_ctrl_mins + b_ctrl_secs/60.0,2)
    except:
        fighterB['basicStatsFor'][11] = 0

#    except:
#        error = soup.find('section', class_='b-fight-details__section').text.strip()
#        fightInfo['details'] = error
#        print('exception:', fightInfo['details'])

#        fighterA['basicStatsFor'] = [None]*12
#        fighterA['advStrStatsFor'] = [None]*12
#        fighterB['basicStatsFor'] = [None]*12
#        fighterB['advStrStatsFor'] = [None]*12

    fighterA['basicStatsAgainst'] = fighterB['basicStatsFor']
    fighterB['basicStatsAgainst'] = fighterA['basicStatsFor']
    fighterA['advStrStatsAgainst'] = fighterB['advStrStatsFor']
    fighterB['advStrStatsAgainst'] = fighterA['advStrStatsFor']

    ######################
    cur.execute('SELECT id FROM Event WHERE name = ? ', (fightInfo['event'], ))
    event_id = cur.fetchone()[0]

    cur.execute('INSERT OR IGNORE INTO Weightclass (name) VALUES (?)', (fightInfo['weightClass'], ))

    cur.execute('SELECT id FROM Weightclass WHERE name = ? ', (fightInfo['weightClass'], ))
    weightclass_id = cur.fetchone()[0]

    cur.execute('''INSERT OR IGNORE INTO Fight (event_id, fight_num, weightclass_id, winner,
        title_fight, method, round, time, total_time, time_format, details, link)
        VALUES ( ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ? )''', ( event_id, fightInfo['fightNum'],
        weightclass_id, fightInfo['winner'], fightInfo['titleFight'], fightInfo['method'],
        fightInfo['round'], fightInfo['time'], total_time, fightInfo['fightLength'],
        fightInfo['details'], fightInfo['link']  ) )

    #######################

    cur.execute('SELECT id FROM Fight WHERE link = ? ', (fightInfo['link'], ))
    fight_id = cur.fetchone()[0]

    cur.execute('''INSERT OR IGNORE INTO FightStats
        (fight_id, fighter_id, opponent, result, kd_for, kd_against, ss_landed_for, ss_att_for,
         ss_landed_against, ss_att_against, ss_pct_for, ss_pct_against, str_landed_for, str_att_for,
         str_landed_against, str_att_against, td_landed_for, td_att_for, td_landed_against, td_att_against,
         td_pct_for, td_pct_against, sub_att_for, sub_att_against, rev_for, rev_against, ctrl_for,
         ctrl_against, head_landed_for, head_att_for, head_landed_against, head_att_against, body_landed_for,
         body_att_for, body_landed_against, body_att_against, leg_landed_for, leg_att_for, leg_landed_against,
         leg_att_against, distance_landed_for, distance_att_for, distance_landed_against, distance_att_against,
         clinch_landed_for, clinch_att_for, clinch_landed_against, clinch_att_against, ground_landed_for,
         ground_att_for, ground_landed_against, ground_att_against )
        VALUES ( ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                 ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ? )''',
        ( fight_id, fighterA['id'], fighterB['id'], fighterA['result'], fighterA['basicStatsFor'][0],
          fighterA['basicStatsAgainst'][0], fighterA['basicStatsFor'][1], fighterA['basicStatsFor'][2],
          fighterA['basicStatsAgainst'][1], fighterA['basicStatsAgainst'][2], fighterA['basicStatsFor'][3],
          fighterA['basicStatsAgainst'][3], fighterA['basicStatsFor'][4], fighterA['basicStatsFor'][5],
          fighterA['basicStatsAgainst'][4], fighterA['basicStatsAgainst'][5], fighterA['basicStatsFor'][6],
          fighterA['basicStatsFor'][7], fighterA['basicStatsAgainst'][6], fighterA['basicStatsAgainst'][7],
          fighterA['basicStatsFor'][8], fighterA['basicStatsAgainst'][8], fighterA['basicStatsFor'][9],
          fighterA['basicStatsAgainst'][9], fighterA['basicStatsFor'][10], fighterA['basicStatsAgainst'][10],
          fighterA['basicStatsFor'][11], fighterA['basicStatsAgainst'][11], fighterA['advStrStatsFor'][0],
          fighterA['advStrStatsFor'][1], fighterA['advStrStatsAgainst'][0], fighterA['advStrStatsAgainst'][1],
          fighterA['advStrStatsFor'][2], fighterA['advStrStatsFor'][3], fighterA['advStrStatsAgainst'][2],
          fighterA['advStrStatsAgainst'][3], fighterA['advStrStatsFor'][4], fighterA['advStrStatsFor'][5],
          fighterA['advStrStatsAgainst'][4], fighterA['advStrStatsAgainst'][5], fighterA['advStrStatsFor'][6],
          fighterA['advStrStatsFor'][7], fighterA['advStrStatsAgainst'][6], fighterA['advStrStatsAgainst'][7],
          fighterA['advStrStatsFor'][8], fighterA['advStrStatsFor'][9], fighterA['advStrStatsAgainst'][8],
          fighterA['advStrStatsAgainst'][9], fighterA['advStrStatsFor'][10], fighterA['advStrStatsFor'][11],
          fighterA['advStrStatsAgainst'][10], fighterA['advStrStatsAgainst'][11] ) )

    print('FighterA Stats Updating...')

    cur.execute('''INSERT OR IGNORE INTO FightStats
        (fight_id, fighter_id, opponent, result, kd_for, kd_against, ss_landed_for, ss_att_for,
         ss_landed_against, ss_att_against, ss_pct_for, ss_pct_against, str_landed_for, str_att_for,
         str_landed_against, str_att_against, td_landed_for, td_att_for, td_landed_against, td_att_against,
         td_pct_for, td_pct_against, sub_att_for, sub_att_against, rev_for, rev_against, ctrl_for,
         ctrl_against, head_landed_for, head_att_for, head_landed_against, head_att_against, body_landed_for,
         body_att_for, body_landed_against, body_att_against, leg_landed_for, leg_att_for, leg_landed_against,
         leg_att_against, distance_landed_for, distance_att_for, distance_landed_against, distance_att_against,
         clinch_landed_for, clinch_att_for, clinch_landed_against, clinch_att_against, ground_landed_for,
         ground_att_for, ground_landed_against, ground_att_against )
        VALUES ( ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                 ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ? )''',
        ( fight_id, fighterB['id'], fighterA['id'], fighterB['result'], fighterB['basicStatsFor'][0],
          fighterB['basicStatsAgainst'][0], fighterB['basicStatsFor'][1], fighterB['basicStatsFor'][2],
          fighterB['basicStatsAgainst'][1], fighterB['basicStatsAgainst'][2], fighterB['basicStatsFor'][3],
          fighterB['basicStatsAgainst'][3], fighterB['basicStatsFor'][4], fighterB['basicStatsFor'][5],
          fighterB['basicStatsAgainst'][4], fighterB['basicStatsAgainst'][5], fighterB['basicStatsFor'][6],
          fighterB['basicStatsFor'][7], fighterB['basicStatsAgainst'][6], fighterB['basicStatsAgainst'][7],
          fighterB['basicStatsFor'][8], fighterB['basicStatsAgainst'][8], fighterB['basicStatsFor'][9],
          fighterB['basicStatsAgainst'][9], fighterB['basicStatsFor'][10], fighterB['basicStatsAgainst'][10],
          fighterB['basicStatsFor'][11], fighterB['basicStatsAgainst'][11], fighterB['advStrStatsFor'][0],
          fighterB['advStrStatsFor'][1], fighterB['advStrStatsAgainst'][0], fighterB['advStrStatsAgainst'][1],
          fighterB['advStrStatsFor'][2], fighterB['advStrStatsFor'][3], fighterB['advStrStatsAgainst'][2],
          fighterB['advStrStatsAgainst'][3], fighterB['advStrStatsFor'][4], fighterB['advStrStatsFor'][5],
          fighterB['advStrStatsAgainst'][4], fighterB['advStrStatsAgainst'][5], fighterB['advStrStatsFor'][6],
          fighterB['advStrStatsFor'][7], fighterB['advStrStatsAgainst'][6], fighterB['advStrStatsAgainst'][7],
          fighterB['advStrStatsFor'][8], fighterB['advStrStatsFor'][9], fighterB['advStrStatsAgainst'][8],
          fighterB['advStrStatsAgainst'][9], fighterB['advStrStatsFor'][10], fighterB['advStrStatsFor'][11],
          fighterB['advStrStatsAgainst'][10], fighterB['advStrStatsAgainst'][11] ) )

    print('FighterB Stats Updating...')
    print()

#    conn.commit()


#####################################
## GetCardInfo()
## takes url of event as input
## returns Card Title, Date and Location
##########################################
def GetCardInfo(url):
#    conn = sqlite3.connect('ufcstatsdb.sqlite')
#    cur = conn.cursor()

    source = requests.get(url).text

    soup = BeautifulSoup(source, 'lxml')

    #Get the Title of the card
    cardTitle = soup.find('span', class_='b-content__title-highlight').text
    cardTitle = cardTitle.strip()

    #Get the Date and Location of the card
    cardDetails = soup.find_all('li', class_='b-list__box-list-item')

    #Have to parse the text b/c of poor formatting w/ spaces and newlines
    dateInfo = cardDetails[0].text.split()
    locationInfo = cardDetails[1].text.split()

    #Remove the Date: and Location: headings from the lists
    del dateInfo[0]
    del locationInfo[0]

    #Put the Date and Location pieces back together in a string
    date = ' '.join(dateInfo)
    location = ' '.join(locationInfo)

    #Loop through list of fights and get the links, weight class and #fights
    tableRows = soup.tbody.find_all('tr', class_='b-fight-details__table-row')

    totalFights = len(tableRows)

    cardInfo = {'title': cardTitle, 'date': date, 'location': location, 'totalFights': totalFights}

    cur.execute('''INSERT OR IGNORE INTO Event (name, date, location, num_fights, link)
        VALUES ( ?, ?, ?, ?, ? )''', ( cardTitle, date, location, totalFights, url ) )

#    conn.commit()

    print("Event:", cardInfo['title'])
    print("Date:", cardInfo['date'])
    print("Location:", cardInfo['location'])
    print("Number of Fights:", cardInfo['totalFights'])
    print("Event URL:", url)

    fightNum = 0

    for fight in tableRows:
        #get links
        link = fight.get('data-link',None)

        #find the weight class for each fight
        columnList = fight.find_all('td')
        weightClass = columnList[6].text.strip()
        fightNum += 1

        print('Fight Number:', fightNum)
        print('Weight Class:', weightClass)

        if weightClass == 'Super Heavyweight' or weightClass == 'Open Weight': continue

        fightInfo = {'event': cardInfo['title'], 'fightNum': fightNum,
         'weightClass': weightClass, 'link': link }

        GetFightInfo(fightInfo)

    conn.commit()

    return cardInfo

################################
##          MAIN
################################
#if __name__ == '__main__':

start_time = time()
conn = sqlite3.connect('ufcstatsdb.sqlite')
cur = conn.cursor()

# in case i want to start from scratch again
#DROP TABLE IF EXISTS Event;
#DROP TABLE IF EXISTS Fight;
#DROP TABLE IF EXISTS Weightclass;
#DROP TABLE IF EXISTS Fighter;
#DROP TABLE IF EXISTS FightStats;

# create all the tables and initialize weightclass lookup table
cur.executescript('''
CREATE TABLE IF NOT EXISTS Event (
    id  INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
    name    TEXT UNIQUE,
    date    TEXT,
    location TEXT,
    num_fights INTEGER,
    link    TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS Weightclass (
    id  INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
    name    TEXT UNIQUE,
    weight  INTEGER,
    abbrev  TEXT,
    male    INTEGER
);

CREATE TABLE IF NOT EXISTS Fighter (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
    name    TEXT,
    nickname    TEXT,
    height  TEXT,
    reach   TEXT,
    weight  TEXT,
    stance  TEXT,
    dob TEXT,
    record  TEXT,
    link    TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS Fight (
    id  INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
    event_id    INTEGER NOT NULL,
    fight_num   INTEGER,
    weightclass_id   INTEGER NOT NULL,
    winner  INTEGER NOT NULL,
    title_fight INTEGER,
    method  TEXT,
    round   INTEGER,
    time    TEXT,
    total_time  REAL,
    time_format INTEGER,
    details TEXT,
    link    TEXT UNIQUE,
    FOREIGN KEY (event_id) REFERENCES Event (id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (weightclass_id) REFERENCES Weightclass (id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (winner) REFERENCES Fighter (id)
        ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS FightStats (
    fight_id    INTEGER NOT NULL,
    fighter_id   INTEGER NOT NULL,
    opponent    INTEGER NOT NULL,
    result  TEXT,
    kd_for  INTEGER,
    kd_against  INTEGER,
    ss_landed_for   INTEGER,
    ss_att_for  INTEGER,
    ss_pct_for     INTEGER,
    ss_landed_against   INTEGER,
    ss_att_against  INTEGER,
    ss_pct_against INTEGER,
    str_landed_for  INTEGER,
    str_att_for INTEGER,
    str_landed_against  INTEGER,
    str_att_against INTEGER,
    td_landed_for   INTEGER,
    td_att_for  INTEGER,
    td_pct_for INTEGER,
    td_landed_against   INTEGER,
    td_att_against  INTEGER,
    td_pct_against INTEGER,
    sub_att_for INTEGER,
    sub_att_against INTEGER,
    rev_for INTEGER,
    rev_against INTEGER,
    ctrl_for    REAL,
    ctrl_against    REAL,
    head_landed_for INTEGER,
    head_att_for    INTEGER,
    head_landed_against INTEGER,
    head_att_against    INTEGER,
    body_landed_for INTEGER,
    body_att_for    INTEGER,
    body_landed_against INTEGER,
    body_att_against    INTEGER,
    leg_landed_for INTEGER,
    leg_att_for    INTEGER,
    leg_landed_against INTEGER,
    leg_att_against    INTEGER,
    distance_landed_for INTEGER,
    distance_att_for    INTEGER,
    distance_landed_against INTEGER,
    distance_att_against    INTEGER,
    clinch_landed_for INTEGER,
    clinch_att_for    INTEGER,
    clinch_landed_against INTEGER,
    clinch_att_against    INTEGER,
    ground_landed_for INTEGER,
    ground_att_for    INTEGER,
    ground_landed_against INTEGER,
    ground_att_against    INTEGER,
    PRIMARY KEY (fight_id, fighter_id),
    FOREIGN KEY (fight_id) REFERENCES Fight (id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (fighter_id) REFERENCES Fighter (id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (opponent) REFERENCES Fighter (id)
        ON DELETE CASCADE ON UPDATE CASCADE
);

INSERT OR IGNORE INTO Weightclass (name, weight, abbrev, male)
    VALUES ('Heavyweight', 265, 'HW', 1);
INSERT OR IGNORE INTO Weightclass (name, weight, abbrev, male)
    VALUES ('Light Heavyweight', 205, 'LHW', 1);
INSERT OR IGNORE INTO Weightclass (name, weight, abbrev, male)
    VALUES ('Middleweight', 185, 'MW', 1);
INSERT OR IGNORE INTO Weightclass (name, weight, abbrev, male)
    VALUES ('Welterweight', 170, 'WW', 1);
INSERT OR IGNORE INTO Weightclass (name, weight, abbrev, male)
    VALUES ('Lightweight', 155, 'LW', 1);
INSERT OR IGNORE INTO Weightclass (name, weight, abbrev, male)
    VALUES ('Featherweight', 145, 'FW', 1);
INSERT OR IGNORE INTO Weightclass (name, weight, abbrev, male)
    VALUES ('Women''s Featherweight', 145, 'WFW', 0);
INSERT OR IGNORE INTO Weightclass (name, weight, abbrev, male)
    VALUES ('Bantamweight', 135, 'BW', 1);
INSERT OR IGNORE INTO Weightclass (name, weight, abbrev, male)
    VALUES ('Women''s Bantamweight', 135, 'WBW', 0);
INSERT OR IGNORE INTO Weightclass (name, weight, abbrev, male)
    VALUES ('Flyweight', 125, 'FLW', 1);
INSERT OR IGNORE INTO Weightclass (name, weight, abbrev, male)
    VALUES ('Women''s Flyweight', 125, 'WFLW', 0);
INSERT OR IGNORE INTO Weightclass (name, weight, abbrev, male)
    VALUES ('Women''s Strawweight', 115, 'WSW', 0);
INSERT OR IGNORE INTO Weightclass (name, weight, abbrev, male)
    VALUES ('Catch Weight', NULL, 'CW', NULL);

INSERT OR IGNORE INTO Fighter (id, name) VALUES (1, 'Draw');
INSERT OR IGNORE INTO Fighter (id, name) VALUES (2, 'No Contest');

''')

#url = 'http://ufcstats.com/statistics/events/completed?page=22'
#url = 'http://ufcstats.com/statistics/events/completed'
url = 'http://ufcstats.com/statistics/events/completed?page=all'
source = requests.get(url).text

soup = BeautifulSoup(source, 'lxml')
body = soup.tbody

#Find the table with all the fight cards
tableRows = body.find_all('tr', class_='b-statistics__table-row')

#skip the empty rows and pass the links for each fight card to GetCardInfo()
for fightCard in tableRows:
    if fightCard.text.isspace()==True: continue

    link = fightCard.a.get('href', None)

    cur.execute('SELECT id FROM Event WHERE link = ? ', (link, ))
    row = cur.fetchone()
    if row is None: GetCardInfo(link)

end_time_secs = time()-start_time
end_time_mins = round(end_time_secs/60.0,2)
print('Finished - Total Time:', end_time_mins, 'min')
