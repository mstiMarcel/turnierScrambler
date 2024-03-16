import re
from bs4 import BeautifulSoup
import requests

# TODO replace the URL with the link to your personal or team matches
# URLs to players and team change every season (id and tid/player id) (no obvious pattern to iterate through all seasons of a player/team)
turnierUrl = "https://www.turnier.de/sport/teammatches.aspx?id=EF2527AC-3040-4220-B35F-AFD7D24332D6&tid=1045"

tableTagPlayer = "ruler matches player"
tableTagTeam = "ruler matches"
# Not hungry enough to break cookie wall
# copied cookies from chrome network recording, expiry might be a problem, works for now
# not really sure how this cookie works, increased potential timestamp s.t. it does not expire
# l= seems to encode the country
cookies = "st=l=1031&exp=66666.7458941898&c=1&cp=23&s=2"

class Match:
    def __init__(self, date, matchType, leagueInfo, home, guest, result):
        self.date = date
        self.matchType = matchType
        self.leagueInfo = leagueInfo
        self.home = home
        self.guest = guest
        self.result = result    
        
    # team matches can be a draw
    def isDraw(self):
        return "winner" in self.guest and "winner" in self.home
        
    def hasWon(self, player):
        if self.isDraw(): return False
        return (player in self.guest and "winner" in self.guest) or (player in self.home and "winner" in self.home)
    
    def isSingle(self):
        return self.matchType in {"HE1", "HE2", "HE3", "DE"}
    
    def isDouble(self):
        return self.matchType in {"HD1", "HD2", "DD"}
    
    def isMixed(self):
        return self.matchType == "GD"
    
    def isValid(self):
        # for player matches: matches not played do not count
        # for team statistic: let the games count that were "o.K."
        return not ("Nicht gespielt" in self.result)

def removeHtmlTags(tdData):
    tdData = str(tdData)
    # tag winners already using the "strong" formatting -> no need to actual look up results
    if "<strong>" in tdData:
        tdData = "winner: " + tdData
    # remove all html tag data
    tdData = re.sub(r"<.*?>", "", tdData)
    return tdData

def extractRowData(row, isPlayer):
    # date, matchType, leagueInfo, home, guest, result
    cleanData = []
    rowData = row.find_all("td")
    
    time = rowData[0 if isPlayer else 1] # <td align="right">Di 05.09.2023 <span class="time">19:00</span></td>
    cleanData.append(removeHtmlTags(time))
    matchType = rowData[1] if isPlayer else "Team" # <td>HD1</td> 
    cleanData.append(removeHtmlTags(matchType))
    leagueInfo = rowData[2] # <td><a href="../draw.aspx?id=EF2527AC-3040-4220-B35F-AFD7D24332D6&draw=70">O19-N2 – O19-N2-KL – (085) Kreisliga Nord 2</a></td>
    cleanData.append(removeHtmlTags(leagueInfo))
    homePlayers = rowData[3 if isPlayer else 6] # <td class="nowrap" align="right"><a class="teamname" href="../teammatch.aspx?id=EF2527AC-3040-4220-B35F-AFD7D24332D6&match=4408">Club 85 Paderborn 3</a><br /><a href="../player.aspx?id=EF2527AC-3040-4220-B35F-AFD7D24332D6&player=8938">Lothar Schnitzler</a><br /><a href="../player.aspx?id=EF2527AC-3040-4220-B35F-AFD7D24332D6&player=17121">Nicolas Potthast</a></td>
    cleanData.append(removeHtmlTags(homePlayers))
    centerMark = rowData[4] # <td align="center">-</td>
    guestPlayers = rowData[5 if isPlayer else 8] # <td class="nowrap"><a class="teamname" href="../teammatch.aspx?id=EF2527AC-3040-4220-B35F-AFD7D24332D6&match=4408">TV 1875 Paderborn 2</a><br /><strong><a href="../player.aspx?id=EF2527AC-3040-4220-B35F-AFD7D24332D6&player=6965">Philipp zur Heiden</a></strong><br /><strong><a class="highlighted" href="../player.aspx?id=EF2527AC-3040-4220-B35F-AFD7D24332D6&player=4888">Marcel Stienemeier</a></strong></td>
    cleanData.append(removeHtmlTags(guestPlayers))
    result = rowData[6 if isPlayer else 9] # <td><span class="score"><span>11-21</span> <span>16-21</span></span></td>
    cleanData.append(removeHtmlTags(result))
    calenderInfo = rowData[7] # <td><a href="../matchcalendarhandler.ashx?code=EF2527AC-3040-4220-B35F-AFD7D24332D6&id=30707&LCID=1031&typeID=11" class="icon-calendar inline-icalendar" title="Export Calendar">Export Calendar</a></td>
    
    return cleanData

def extractSoupFromLink(link):
    htmlResponse = requests.get(turnierUrl, headers={'User-Agent': 'Custom', "cookie": cookies})
    if(htmlResponse.status_code != 200):
        print("error, status: ", htmlResponse.status_code)
        # check header and cookies
        raise ConnectionRefusedError("no connection possible to " + link)
    # Prepare the soup
    return BeautifulSoup(htmlResponse.text, "html.parser")

def extractMatchesFromTable(matchesTable, isPlayer):
    matches = []
    tableData = matchesTable.find("tbody").find_all("tr")
    
    for row in tableData:
        rowData = extractRowData(row, isPlayer)
        # date, matchType, leagueInfo, home, guest, result
        matches.append(Match(rowData[0], 
                             rowData[1],
                             rowData[2],
                             rowData[3],
                             rowData[4],
                             rowData[5],
                             ))
        
    return matches

def removeMatchesNotPlayed(matches):
    cleanMatches = []
    for match in matches:
        if match.isValid(): cleanMatches.append(match)
    return cleanMatches
    
def getPlayerName(soup):
    title = removeHtmlTags(soup.find("title"))
    return title.strip().split(" - ")[-1]    

def getTeamName(soup):
    title = removeHtmlTags(soup.find("title"))
    title = title.strip().split(" - ")[-2]   
    return title.split(":")[1].split("(")[0].strip()

def getWins(matches, player):
    wins = []
    for match in matches:
        if match.hasWon(player): wins.append(match)
    return wins

def getDraws(matches, player):
    draws = []
    for match in matches:
        if match.isDraw(): draws.append(match)
    return draws

def winLossStatistic(matches, player, isPlayer=True):
    if(matches is None or len(matches) == 0):
        return "No matches played"
    wins = len(getWins(matches, player))
    total = len(matches)
    percentage = round((wins / total) * 100, 2)
    statString = "Won %d of %d (%d%s)" % (wins, total, percentage, "%")
    if(not isPlayer):
        draws = len(getDraws(matches, player))
        percentage = round((draws/total) * 100, 2)
        drawString = ", draws: %d of %d (%d%s)" % (draws, total, percentage, "%")
        statString += drawString
    return statString

# weekDay is the first two letters of the German name, e.g. "Di" for Dienstag
def getMatchesByWeekDay(matches, weekDay):
    dayMatches = []
    for match in matches:
        if weekDay in match.date: dayMatches.append(match)
    return dayMatches

def getWorkDayMatches(matches):
    workMatches = []
    workDays = {"Mo", "Di", "Mi", "Do", "Fr"}
    for day in workDays:
        workMatches.extend(getMatchesByWeekDay(matches, day))
    return workMatches

def getWeekendMatches(matches):
    weekEndMatches = []
    weekEndDays = {"Sa", "So"}
    for day in weekEndDays:
        weekEndMatches.extend(getMatchesByWeekDay(matches, day))
    return weekEndMatches

def getSingles(matches):
    singles = []
    for match in matches:
        if match.isSingle(): singles.append(match)
    return singles
    
        
def getDoubles(matches):
    doubles = []
    for match in matches:
        if match.isDouble(): doubles.append(match)
    return doubles
        
def getMixed(matches):
    mixed = []
    for match in matches:
        if match.isMixed(): mixed.append(match)
    return mixed

def printStatistics(matches, player, isPlayer=True):
    if(matches is None or len(matches) == 0):
        return "No matches played"
    
    print("monday: ", winLossStatistic(getMatchesByWeekDay(matches, "Mo"), player, isPlayer=isPlayer))
    print("saturday: ", winLossStatistic(getMatchesByWeekDay(matches, "Sa"), player, isPlayer=isPlayer))
    workDayMatches = getWorkDayMatches(matches)
    print("work days: ", winLossStatistic(workDayMatches, player, isPlayer=isPlayer))
    weekendMatches = getWeekendMatches(matches)
    print("weekend matches: ", winLossStatistic(weekendMatches, player, isPlayer=isPlayer))
    print("\n------------------------------------------------------------------------------\n")
    
def checkPlayerLink(soup):
    title = removeHtmlTags(soup.find("title"))
    print(title)
    return "Spieler" in title

def main():
    soup = extractSoupFromLink(turnierUrl)
    isPlayerLink = checkPlayerLink(soup)
    print("Analyzing ", "player" if isPlayerLink else "team", " statistics")
          
    player = getPlayerName(soup) if isPlayerLink else getTeamName(soup)
    matchesTable = soup.find("table", tableTagPlayer if isPlayerLink else tableTagTeam)
    matches = extractMatchesFromTable(matchesTable, isPlayerLink)
    # for player statistics: games not played if the other team had not enough players, do not count
    # for team statistic: let the games count that were "o.K."
    matches = removeMatchesNotPlayed(matches)
    
    print(player)    
    print("total: ", winLossStatistic(matches, player, isPlayer=isPlayerLink))
    printStatistics(matches, player, isPlayer=isPlayerLink)
    
    if isPlayerLink:
        singles = getSingles(matches)
        print("singles: ", winLossStatistic(singles, player))
        printStatistics(singles, player)
        
        doubles = getDoubles(matches)
        print("doubles: ", winLossStatistic(doubles, player))
        printStatistics(doubles, player)
        
        mixed = getMixed(matches)
        print("mixed: ", winLossStatistic(mixed, player))
        printStatistics(mixed, player)

if __name__ == "__main__":
    main()