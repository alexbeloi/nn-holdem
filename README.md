# nn-holdem
Code to build and teach a neural network to play a game of texas hold'em

### Current Status
The following things need to be built before the project is complete

* ~~holdem dealer~~
* pot splitting
* neural network
* coevolutionary learning system

Additional (optional)

* learning from existing real world game history
* competition heuristics
*

### Holdem Implementation

We built a basic single table no limit holdem game. Both dealer and player run a SimpleXMLRPCServer to exchange game data about board state and player moves.

The current implementation is meant to simulate a cash game. In the future, we will expand to accomodate multi-table tournament play.

## Neural network

The following is to be implemented

### Input data

|                 | Description |
| :---------------| :-----------|
| Pot             | Chips available to win in current hand of play |
| ToCall          | Amout of chips needed to add to pot in order stay in current hand of play |
| Players         | Number of opponents |
| Stacks          | The amount of chips(money) each player has |
| Pocket cards    | Cards in personal hand |
| Community cards | Shared cards available for all players to use |
| BigBlind        | Size of minimum stake |
| Button          | Position of player last to act in a given round |

### Layers

We expect the number of nodes needed in each layer to be about **80-X-1**. The output will be interpreted as a bet amount, which will then be parsed as either raise, call, check, fold.

Alternative would be an **80-X-5** setup with the first four outputs in *[0,1]* denoting network confidence in raise, call, check, fold (resp.) and the last output denoting bet ammount normalized to personal stack or pot size.

### Learning

We plan to teach networks through coevolution + hall-of-fame. We spawn *~10000* random networks and have them compete with each other in 8-seat tables, we pick the top *100* networks and use them to spawn *10000* additional child agents through randomly biased averaging of the parent's weights and repeat with new generation of child agents + hall-of-famers.

The hall-of-fame agents are always preserved and never fall out of use. As the hall-of-fame becomes large, we randomly choose which hall-of-famers to include in the next generation, but the total pool of hall-of-famers is never allowed to diminish.

## Literature
* coevolution and hall-of-fame heuristics:
http://www2.cs.uregina.ca/~hilder/refereed_conference_proceedings/cig09.pdf
* Overview of artificial intelligence strategies for texas hold'em poker: http://poker-ai.org/archive/pokerai.org/public/aith.pdf
* New York Times article on computer poker: http://www.nytimes.com/2013/09/08/magazine/poker-computer.html?_r=0
