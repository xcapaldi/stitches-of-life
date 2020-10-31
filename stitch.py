#!/usr/bin/env python3

"""
In a knitted stitch:

* Wale - width of stitch * Course - height of stitch

The ratio of these is dependent on yarn weight, needle size and knitter.
It seems to fall between 1:1 and 1:1.85 (stitches:rows).
Maybe we will allow the user to define this.
"""


import pygame
import random as rnd
import time

def test_full_setup(n):
    """Simple function to generate full grid of cells."""
    for x in range(n):
        for y in range(n):
            Stitch(x,y)
            Stitch.stitches[(x,y)].vital = True if round(rnd.random()) == 1 else False

def test_glider():
    """Generate a glider."""
    for x in range(100):
        for y in range(100):
            Stitch(x,y)

    Stitch.stitches[(11,12)].alive = True
    Stitch.stitches[(12,13)].alive = True
    Stitch.stitches[(13,11)].alive = True
    Stitch.stitches[(13,12)].alive = True
    Stitch.stitches[(13,13)].alive = True
    
def test_blinker():
    """Generate a blinker."""
    for x in range(100):
        for y in range(100):
            Stitch(x,y)

    Stitch.stitches[(10,10)].alive = True
    Stitch.stitches[(11,10)].alive = True
    Stitch.stitches[(12,10)].alive = True
        
class App:
    def __init__(self):
        self.running = True
        self.screen = None
        self.size = self.width, self.height = 1000, 1000
        self.flags = None

    def on_init(self):
        pygame.init()
        self.screen = pygame.display.set_mode(self.size) #self.flags
        self.screen.fill((255, 255, 255))
        self.running = True
            
        test_full_setup(100)
        for stitch in list(Stitch.stitches.values()):
            stitch.find_neighbors()

    def on_event(self, event):
        if event.type == pygame.QUIT:
            self.running = False

    def on_loop(self):
        for stitch in list(Stitch.stitches.values()):
            stitch.cycle
            stitch.check_neighbors()
            stitch.progress()
        #time.sleep(0.1)

    def on_render(self):
        self.screen.fill((255, 255, 255))
        for stitch in list(Stitch.stitches.values()):
            stitch.render(self)
        pygame.display.update()

    def on_cycle(self):
        for stitch in list(Stitch.stitches.values()):
            stitch.cycle()
            
    def on_cleanup(self):
        pygame.quit()

    def on_execute(self):
        if self.on_init() == False:
            self.running = False

        while self.running:
            for event in pygame.event.get():
                self.on_event(event)
            self.on_loop()
            self.on_render()
            self.on_cycle()
        self.on_cleanup()

# we have two spaces
# screen space
# and world space
# world space is purely a collection of data in the world

class Stitch:
    stitches = {}
    def __init__(self, x, y):
        self.position = (x, y)
        # this will hold the current state and the state for the next time step
        self.alive = False
        self.vital = False
        # list of neighbors
        # originally I tracked each neighbor but that isn't required
        # I can't simply calculate neighbors by position since
        # some neighbors won't fall adjacent on the cartesian grid
        self.neighbors = [] # (x1, y1), (x2, y2)
        # this could also hold reference to actual neighbor objects but I
        # think that is less computationally efficient when it comes time to calculate neighbors
        # add stitch to dictionary of stitches in class
        # can lookup by position and get that object in return
        Stitch.stitches[self.position] = self

    def find_neighbors(self):
       """
       Find all simple neighboring stitches.

         x ->
       y v v v v v
       | v n n n v
       V v n V n v
         v n n n v
         v v v v v
       
       Note that this isn't always the case at boundaries but we will leave that logic for later.
       """
       x, y = self.position

       for i in range(3):
           for j in range(3):
               try:
                   self.neighbors.append(self.stitches[(x - 1 + i, y - 1 + j)].position)
               except:
                   pass

       # this cell will be added by default so we must delete at the end
       self.neighbors.remove(self.position)
       

    def check_neighbors(self):
        self.live_neighbors = 0
        for neighbor in self.neighbors:
            if self.stitches[neighbor].alive:
                self.live_neighbors += 1

    def propogate(self):
        if self.live_neighbors == 3:
            self.vital = True

    def live_or_die(self):
        # die from solitude
        if self.live_neighbors < 2:
            self.vital = False
        # die from overcrowding
        elif self.live_neighbors > 3:
            self.vital = False
        # survive
        else:
            self.vital = True

    def progress(self):
        if self.alive:
            self.live_or_die()
        else:
            self.propogate()

    def cycle(self):
        self.alive = self.vital

    def delete(self):
        del Stitch.stitches[self.position]
        
    def render(self, app):
        """
        Provide app object to this function so it can render to the active screen.
        """

        if self.alive:
            # make the rectangle call more clear
            x, y = self.position 
            # (x, y, width, height)
            red = round(rnd.random()*255)
            green = round(rnd.random()*255)
            blue = round(rnd.random()*255)
            pygame.draw.rect(app.screen, (0, 0, 0), (x*10, y*10, 10, 10))
      
if __name__ == "__main__":
    myApp = App()
    myApp.on_execute()

    
