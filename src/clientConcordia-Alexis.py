import random
import re
from twisted.internet import protocol
from twisted.internet import reactor
from twisted.protocols.basic import LineReceiver

from hockey.action import Action


move_cheat =[(0, -1),(1, -1),(1, 0),(1, 1),(0, 1),(-1, 1),(-1, 0),(-1, -1)]

class HockeyClient(LineReceiver, object):
    def __init__(self, name, debug):
        self.name = name
        self.start_pos=None
        self.current_pos=(0,0)
        self.debug = debug
        self.board=[[[False for x in range(8)] for i in range(11)] for i in range(11)]
        self.goal=None
        self.enemy_goal=None

        for i in range(11):
            self.board[i][0]=[True for x in range(8)]
            self.board[i][10]=[True for x in range(8)]
            if i==4:
                self.board[i][0][0]=False
                self.board[i][0][6]=False
                self.board[i][0][7]=False
                self.board[i][10][4]=False
                self.board[i][10][5]=False
                self.board[i][10][6]=False
            elif i==6:
                self.board[i][0][0]=False
                self.board[i][0][1]=False
                self.board[i][0][2]=False
                self.board[i][10][2]=False
                self.board[i][10][3]=False
                self.board[i][10][4]=False
            else:
                self.board[i][0][0]=False
                self.board[i][0][1]=False
                self.board[i][0][2]=False
                self.board[i][0][6]=False
                self.board[i][0][7]=False
                self.board[i][10][2]=False
                self.board[i][10][3]=False
                self.board[i][10][4]=False
                self.board[i][10][5]=False
                self.board[i][10][6]=False

        for i in range(11):

            self.board[0][i]=[True for x in range(8)]
            self.board[10][i]=[True for x in range(8)]

            self.board[0][i][0]=False
            self.board[0][i][4]=False
            self.board[0][i][5]=False
            self.board[0][i][6]=False
            self.board[0][i][7]=False

            self.board[10][i][0]=False
            self.board[10][i][4]=False
            self.board[10][i][5]=False
            self.board[10][i][6]=False
            self.board[10][i][7]=False


    '''def get_neighbours(self,pt1):
	    x,y=pt1
        neighbours=[self.board[i][j] for i in range(max(x-1,0),min(x+1,10)) for j in range(max(y-1,0),min(y+1,10))]
	    return neighbours'''

    def connectionMade(self):
        self.sendLine(self.name)

    def sendLine(self, line):
        super(HockeyClient, self).sendLine(line.encode('UTF-8'))

    def lineReceived(self, line):
        line = line.decode('UTF-8')
        if self.debug:
            print('Server said:', line)
        if self.start_pos is None and "ball" in line:
            words=line.split('(')[1]
            words=words.split(')')[0]
            posits=words.split(',')
            self.start_pos=(int(posits[0]),int(posits[1]))
            self.current_pos=self.start_pos
            print("Current:{}".format(self.current_pos))

        elif self.goal is None and "your goal is" in line:
            if "north" in line:
                self.enemy_goal=[(4,-1),(5,-1)]
                self.goal=[(4,12),(5,12)]
            elif "south" in line:
                self.goal=[(4,-1),(5,-1)]
                self.enemy_goal=[(4,12),(5,12)]

        elif '{} is active player'.format(self.name) in line or 'invalid move' in line:
            if 'invalid move' in line:
                result = Action.from_number(random.randint(0, 7))
                self.sendLine(result)
            else:
                self.play_game()

        if 'did go' in line:
            words=line.split()
            directions=words[words.index('go')+1:]
            moves=[]
            for dir in directions:
                try:
                    moves.append(Action.move[dir])
                except KeyError:
                    pass

            move=moves[0] if len(moves)==1 else (sum([d[0] for d in moves]),sum([d[1] for d in moves]))

            self.current_pos=(self.current_pos[0]+move[0],self.current_pos[1]+move[1])
            print("{}".format(self.current_pos))

            self.board[self.current_pos[0]-move[0]][self.current_pos[1]-move[1]][move_cheat.index(move)]=True



    def getNextMove(self,x,y):
        return (self.current_pos[0]+x,self.current_pos[1]+y)

    def canMakeMove(self,x,y):
        try:
            if (self.current_pos[0]+x,self.current_pos[1]+y) in self.enemy_goal:
                return True
            can_move= not self.board[self.current_pos[0]][self.current_pos[1]][move_cheat.index((x,y))]
            newx,newy=(self.getNextMove(x,y))
            if newx==11 or newy==11 or newx==0 or newy==0:
                return False
            return can_move
        except IndexError:
            return False

    def can_ricochet(self,x,y):
        return x>=11 or y>=11 or x<=0 or y<=0 or (any(self.board[x][y]))

    def cascadeRicochets(self,x,y,depth):
        values = [0]*3
        goalY = self.enemy_goal[1][1]

        if depth == 4:
            return values

        direction = 0;
        if y-goalY > 0:
            direction = -1
        else:
            direction = 1
        if self.canMakeMove(-1,direction):
            if self.can_ricochet(x-1, y+direction):
                values[0] += max(self.cascadeRicochets(x-1, y+direction, depth+1))+1
        if self.canMakeMove(0,direction):
            if self.can_ricochet(x, y+direction):
                values[1] += max(self.cascadeRicochets(x, y+direction, depth+1))+1
        if self.canMakeMove(1,direction):
            if self.can_ricochet(x+1, y+direction):
                values[2] += max(self.cascadeRicochets(x+1, y+direction, depth+1))+1
        return values

    def play_game(self):
        possibleMovesScores = []

        for val in Action.Name.values():
            (x,y)=Action.move[val]
            if self.canMakeMove(x,y):
                moveScore=0
                (new_x,new_y)=self.getNextMove(x,y)
                if self.can_ricochet(new_x, new_y):
                    moveScore+=0.5
                if (new_x,new_y) in self.enemy_goal:
                    moveScore+=5.0
                min_dist=abs(new_x-self.enemy_goal[0][0])+abs(new_y-self.enemy_goal[0][1])
                moveScore-=min_dist
                possibleMovesScores.append(moveScore)
            else:
                possibleMovesScores.append(-1000)

        best_move=possibleMovesScores.index(max(possibleMovesScores))

        result = Action.from_number(best_move)
        print(self.current_pos)
        print(result)

        self.sendLine(result)


class ClientFactory(protocol.ClientFactory):
    def __init__(self, name, debug):
        self.name = name
        self.debug = debug

    def buildProtocol(self, addr):
        return HockeyClient(self.name, self.debug)

    def clientConnectionFailed(self, connector, reason):
        if self.debug:
            print("Connection failed - goodbye!")
        reactor.stop()

    def clientConnectionLost(self, connector, reason):
        if self.debug:
            print("Connection lost - goodbye!")
        reactor.stop()


name = "MacroHard-Conco{}".format(random.randint(0, 999))

f = ClientFactory(name, debug=True)
reactor.connectTCP("localhost", 8023, f)
reactor.run()
