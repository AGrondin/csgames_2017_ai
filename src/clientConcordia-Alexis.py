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
        self.board=[[[False for x in range(8)] for i in range(15)] for i in range(15)]
        self.goal=None
        self.enemy_goal=None
        self.owns_power_up=False
        self.power_up_position=None

    def is_wall(self,pt):
        is_side_wall=pt[0] not in [0,15]
        is_bottom_wall=pt[1] not in [0,15] and pt[0] not in [6,7,8]
        return is_side_wall or is_bottom_wall

    def get_neighbours(self,pt1):
        x,y=pt1
        #Not walls
        neighbours=[]
        for i in range(max(x-1,0),min(x+1,10)):
            for j in range(max(y-1,0),min(y+1,10)):
                if not (self.is_wall(pt1) and self.is_wall((i,j))):
                    neighbours.append((i,j))
	
        if len(neighbours) == 0:
            print("No neighbours")

        return neighbours


    def get_move_idx(self,pt1,pt2):
        try:
            return move_cheat.index((pt1[0]-pt2[0],pt1[1]-pt2[1]))
        except ValueError:
            print("Move index not found")
            return 10

    def get_position(self,pt):
        return self.board[pt[0]][pt[1]]

    def get_edge_available(self,pt1,pt2):
        try:
            occupied = self.get_position(pt1)[self.get_move_idx(pt1,pt2)]\
                       or self.get_position(pt2)[self.get_move_idx(pt2,pt1)]
            return not occupied
        except IndexError:
            print("Move not found")
            return False


    def get_possible_moves(self,point):
        moves=[]

        for pt in self.get_neighbours(point):
            if self.get_edge_available(point,pt):
                moves.append(self.get_move_idx(point,pt))

        return moves

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
                self.enemy_goal=[(6,-1),(7,-1),(8,-1)]
                self.goal=[(6,15),(7,15),(8,15)]
            elif "south" in line:
                self.goal=[(6,-1),(7,-1),(8,-1)]
                self.enemy_goal=[(6,15),(7,15),(8,15)]

        elif '{} is active player'.format(self.name) in line or 'invalid move' in line:
            if 'invalid move' in line:
                result = Action.from_number(random.randint(0, 7))
                self.sendLine(result)
            else:
                self.play_game()

        if 'polarity' in line:
            temp=self.enemy_goal
            self.enemy_goal=self.goal
            self.goal=self.enemy_goal
        
        

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

        return (any(self.board[x][y]) or x==11 or y==11 or x==0 or y==0)

    def distance_goals(self,pt=self.current_pos,is_enemy_goal=True):
	    return min([distance(pt,goal_pt) for goal_pt in self.enemy_goal])

    def distance(self,pt1,pt2):
        return max([abs(pt1[0]-pt2[0]),abs(pt1[1]-pt2[1])])

    def min_distance_power_up(self):
        return min([distance(

    def play_game(self):
        possibleMovesScores = []

        print("Moves:")
        print(self.get_possible_moves(self.current_pos))

        for val in Action.Name.values():
            (x,y)=Action.move[val]
            if self.canMakeMove(x,y):
                moveScore=0
                (new_x,new_y)=self.getNextMove(x,y)
                if self.can_ricochet(new_x, new_y):
                    moveScore+=0.5
                if (new_x,new_y) in self.enemy_goal:
                    moveScore+=5.0
                min_dist=self.distance_goals((new_x,new_y))
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
