# nn-holdem
Code to build and teach a neural network to play a game of texas hold'em. The code includes a bare-bones console hold'em table, neural network, and neural network trainer. A human players can play on via console but it would be nice to add a GUI frontend.

As of this writing, it has all of the features originally intended to be designed.

### Current Status
The following things need to be built before the project is complete

* ~~hold'em dealer~~
* ~~pot splitting~~
* ~~incorporate hand rank evaluator~~ (using forked package [dueces](https://github.com/alexbeloi/deuces/tree/convert2to3) converted to python3)
* ~~neural network~~
* ~~**learning system**~~
  * ~~Hall of fame generator~~
  * ~~Child agent spawner~~
  * ~~Tournament system~~

Additional (2nd stage)
* ~~Train seperate neural network to replace rank evaluator and/or win percentage analyzer~~
  * speed up training
* learning from existing real world game history
* competition heuristics

Strong potential branches
* Use a Recurrent Neural Network with LSTM modules
  * accept streams of data (turns)
  * replace evolutionary learning with backpropogation through time (must faster)
* Q-learning and MDPs seem perfect for poker, how to incorporate Q-learning into neural net?

Bonus features
* GUI frontend for human player

### Usage
Running from play.py is simplest way to test things out (although the ai opponents are just random for now)
```python
$ cat play.py
from holdem import Table, TableProxy, PlayerControl, PlayerControlProxy

seats = 8
# start an table with 8 seats
t = Table(seats)
tp = TableProxy(t)

# controller for human meat bag
h = PlayerControl("localhost", 8001, 1, False)
hp = PlayerControlProxy(h)

print('starting ai players')
# fill the rest of the table with ai players
for i in range(2,seats+1):
    p = PlayerControl("localhost", 8000+i, i, True)
    pp = PlayerControlProxy(p)
```

To start an 8 person table with yourself + (seven) unlearned ai opponents simply run
```python
$ python3 play.py
Player  1  Joining game
starting ai players
Player  2  Joining game
Player  3  Joining game
Player  4  Joining game
Player  5  Joining game
Player  6  Joining game
Player  7  Joining game
Player  8  Joining game
Player 4 ['raise', 1475]
Player 5 ['fold', -1]
Player 6 ['fold', -1]
Player 7 ['fold', -1]
Player 8 ['fold', -1]
Stacks:
1 :  2000(P)(Button)(me)
2 :  1990(P)
3 :  1975(P)
4 :  525(P)
5 :  2000
6 :  2000
7 :  2000
8 :  2000
Community cards:  
Pot size:  1510
Pocket cards:   [ 3 ♠ ] , [ 3 ♣ ]  
To call:  1475
1) Raise
2) Call
3) Fold
Choose your option:
```

For now, if you want to play against *smart* ai opponents, you'll have to run the ai trainer `go_ai.py` to start the training algorithm. This is a significant time investment, at some point I'll pre-include some trained networks.

### Holdem Implementation

We built a basic single table no limit hold'em game. Both dealer and player run a SimpleXMLRPCServer to network board state and player moves.

The current implementation is meant to simulate a cash game.

## Neural network

The neural network uses mixed binary and continuous data.

Based on the recommendation of some literature on modeling systems with mixed data, we use *effect coding* **{-1,1}** instead of *dummy coding* **{0,1}** for the binary variables. For the continuous variables (chip ammounts), we normalize by the bigblind and center all values. Ideally we would center values around their means, for the stack sizes we can use the mean stack size at any given table but for other continuous inputs we center around mean stack size.

The activation function we're currently using is **tanh**, but since we aren't going to use backpropogation we may want to consider nondifferentiable activation functions.

### Input data

| Continuous      | Description |
| :---------------| :-----------|
| Pot             | Chips available to win in current hand of play |
| To Call         | Amout of chips needed to add to pot in order stay in current hand of play |
| Last Raise      | The most recent raise ammount for current round |
| Player Stacks   | Ammount of chips(money) each player has |
| Win percentage  | Chance to win assuming all unknown cards are uniformly distributed |

| Binary          | Description |
| :---------------| :-----------|
| Player position | Own position at the table |
| Players in hand | Which players are still currently in the game |
| Player betting  | Which player(s) is betting |

Originally we tried to use binary data to represent pocket cards and community cards, this lead to too little variance on the part of the network. We were unable to select for any interesting behavior because the behavior was always the same (fold). We scaled down the problem by replacing the 200+ binary inputs (required to represent card data) with a proxy value representing the chance for the player to win (assuming all current and future unknown cards are uniformly random).

For speed, we compute win percentage using a Monte Carlo simulation. The analyzer class is from [PokerTude](https://github.com/neynt/pokertude) adapted to use the [Deuces](https://github.com/alexbeloi/deuces/tree/convert2to3) Deck, Card and Evaluator classes for speedup.

A more sophisticated approach would be to attach another neural network which tries to predict the opponents hands (e.g. http://www.spaz.ca/aaron/poker/nnpoker.pdf) and use this in place of a uniform distribution for the opponent's hand.

### Layers

We use a **32-20-5** setup with the first four outputs in *[0,1]* denoting network confidence in raise, call, check, fold (resp.) and the last output denoting bet ammount normalized to personal stack or pot size.

### Learning

We learn through coevolution + hall-of-fame. We spawn *~1000-2000* random networks and have them compete with each other in 8-seat tables. Each table also has two hard-coded bots, one of which is *check/call* only and one a random bot. If a neural network wins a table (is the last remaining player), then we save this network to the hall of fame and move it along to the next stage in the tournament.

Once a substantial hall-of-fame is generated, we use the hall-of-famers to generate child agents. A child agent's weights are a biased sum of the weights of the parents.

The hall-of-fame agents are always preserved and never fall out of use. As the hall-of-fame becomes large, we (uniformly) randomly choose hall-of-famers to include in the next epoch, but the total pool of hall-of-famers is never allowed to diminish.

## Literature
* coevolution and hall-of-fame heuristics:
http://www2.cs.uregina.ca/~hilder/refereed_conference_proceedings/cig09.pdf
* optimal learning rate:
http://arxiv.org/pdf/1206.1106.pdf
* Overview of artificial intelligence strategies for texas hold'em poker: http://poker-ai.org/archive/pokerai.org/public/aith.pdf
* New York Times article on computer poker: http://www.nytimes.com/2013/09/08/magazine/poker-computer.html?_r=0

## License
The MIT License (MIT)

Copyright (c) 2016 Aleksander Beloi (beloi.alex@gmail.com)

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
