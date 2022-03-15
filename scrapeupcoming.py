from bs4 import BeautifulSoup
import requests
import sqlite3
import csv

conn = sqlite3.connect('ufcstatsdb.sqlite')
cur = conn.cursor()

url = 'http://ufcstats.com/event-details/1f9344211ca7fd60'

source = requests.get(url).text

soup = BeautifulSoup(source, 'lxml')

#Loop through list of fights and get the links, weight class and #fights
tableRows = soup.tbody.find_all('tr', class_='b-fight-details__table-row')

fightNum = 1

header = ['Fight', 'Fighter', 'Division', 'Height', 'Reach', '#Fights', 'Total Time', 'Avg Fight Time',
    'SLpM', 'Str%', 'SApM', 'Str Def', 'TD/15', 'TD%', 'TD Def', 'Ctrl For', 'Ctrl Against',
    'SS For', 'SS Att For', 'SS Against', 'SS Att Against', 'Str For', 'Str Att For',
    'Str Against', 'Str Att Against', 'TotalTD', 'TD Att For', 'TotalTD Against', 'TD Att Against',
    'Sub Att For', 'Sub Att Against', 'Reversals For', 'Reversals Against', 'KD For', 'KD Against']

#open csv file
with open('cardstats.csv', 'w', newline='') as csv_file:
    csv_writer = csv.writer(csv_file)
    csv_writer.writerow(header)

    #get fight info
    for row in tableRows:
        bout = row.find_all('td', class_='b-fight-details__table-col')
        division = bout[6].text.strip()

        fight = row.find_all('a')[:2]

        for fighter in fight:
            fname = fighter.text.strip()
            flink = fighter.get('href', None)

            #get stats from db
            cur.execute('SELECT id FROM Fighter WHERE link = ? ', (flink, ))
            fid = cur.fetchone()
            print(fid)

            if fid is not None:
                cur.execute('SELECT height, reach FROM Fighter WHERE id = ? ', (fid[0], ))
                measurements = cur.fetchone()
                height = measurements[0]
                reach = measurements[1]

                cur.execute('SELECT COUNT(*) AS numFights FROM FightStats WHERE fighter_id = ? ', (fid[0], ))
                numFights = cur.fetchone()[0]

                cur.execute('''SELECT SUM(total_time) FROM Fight JOIN FightStats
                    ON Fight.id = FightStats.fight_id
                    WHERE fighter_id = ? ''', (fid[0], ))

                totalMins = cur.fetchone()[0]
                avgMins = round(totalMins/numFights,2)

                cur.execute('''SELECT SUM(FightStats.ss_landed_for), SUM(FightStats.ss_att_for),
                SUM(FightStats.ss_landed_against), SUM(FightStats.ss_att_against),
                SUM(FightStats.td_landed_for), SUM(FightStats.td_att_for), SUM(FightStats.td_landed_against),
                SUM(FightStats.td_att_against), SUM(FightStats.kd_for), SUM(FightStats.kd_against),
    	        SUM(FightStats.sub_att_for), SUM(FightStats.sub_att_against), SUM(FightStats.rev_for),
                SUM(FightStats.rev_against), SUM(FightStats.str_landed_for), SUM(FightStats.str_att_for),
                SUM(FightStats.str_landed_against), SUM(FightStats.str_att_against), SUM(FightStats.ctrl_for),
				SUM(FightStats.ctrl_against)
                FROM FightStats WHERE fighter_id = ? ''', (fid[0], ))

                stats = cur.fetchone()
                ss_landed_for = stats[0]
                ss_att_for = stats[1]
                ss_landed_against = stats[2]
                ss_att_against = stats[3]
                SLpM = round(ss_landed_for/totalMins,2)
                str_pct = round(ss_landed_for/ss_att_for,2)
                SApM = round(ss_landed_against/totalMins,2)
                str_def = round((1-ss_landed_against/ss_att_against),2)
                totalTD = stats[4]
                td_att_for = stats[5]
                TDper15 = round(totalTD/totalMins*15,2)
                try: TD_pct = round(totalTD/td_att_for,2)
                except: TD_pct = 0
                TD_against = stats[6]
                td_att_against = stats[7]
                try: TD_def = round((1-TD_against/td_att_against),2)
                except: TD_def = 0
                KD_for = stats[8]
                KD_against = stats[9]
                sub_for = stats[10]
                sub_against = stats[11]
                rev_for = stats[12]
                rev_against = stats[13]
                str_landed_for = stats[14]
                str_att_for = stats[15]
                str_landed_against = stats[16]
                str_att_against = stats[17]
                ctrl_for = stats[18]
                ctrl_against = stats[19]

#                cur.execute('''SELECT SUM(ROUND(strftime('%M', '00:0' || ctrl_for) +
#                (strftime('%S', '00:0' || ctrl_for))/60.0,2)) AS totalCtrlFor,
#    	        SUM(ROUND(strftime('%M', '00:0' || ctrl_against) + (strftime('%S', '00:0' || ctrl_against))/60.0,2))
#                AS totalCtrlAgainst
#                FROM FightStats WHERE FightStats.fighter_id = ? ''', (fid[0], ))

#                control = cur.fetchone()
#                ctrl_for = round(control[0],2)
#                ctrl_against = round(control[1],2)

            else:
                height = None
                reach = None
                numFights = 0
                totalMins = 0
                avgMins = 0
                ss_landed_for = 0
                ss_att_for = 0
                ss_landed_against = 0
                ss_att_against = 0
                SLpM = 0
                str_pct = 0
                SApM = 0
                str_def = 0
                totalTD = 0
                td_att_for = 0
                TDper15 = 0
                TD_pct = 0
                TD_against = 0
                td_att_against = 0
                TD_def = 0
                KD_for = 0
                KD_against = 0
                sub_for = 0
                sub_against = 0
                rev_for = 0
                rev_against = 0
                ctrl_for = 0
                ctrl_against = 0
                str_landed_for = 0
                str_att_for = 0
                str_landed_against = 0
                str_att_against = 0

                #write to csv

            fighter_list = [fightNum, fname, division, height, reach, numFights, totalMins, avgMins,
                SLpM, str_pct, SApM, str_def, TDper15, TD_pct, TD_def, ctrl_for, ctrl_against,
                ss_landed_for, ss_att_for, ss_landed_against, ss_att_against, str_landed_for,
                str_att_for, str_landed_against, str_att_against, totalTD, td_att_for,
                TD_against, td_att_against, sub_for, sub_against, rev_for, rev_against, KD_for, KD_against]
            flist = fighter_list.copy()
            csv_writer.writerow(flist)
        fightNum += 1


#print(fighter_list)
