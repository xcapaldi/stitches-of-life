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
        self.offset = (0, 0)
        self.rmb = False
        self.scale = 10

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
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.rmb = True
            print(round(pygame.mouse.get_pos()[0]/self.scale), round(pygame.mouse.get_pos()[1]/self.scale))
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.rmb = False
        elif event.type == pygame.MOUSEMOTION:
            if self.rmb:
                self.offset = (round(self.offset[0] - (event.rel[0]/self.scale)), round(self.offset[1] - (event.rel[1]/self.scale)))
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 4:
            # capture mouse position in world space
            mouse_init = (round(pygame.mouse.get_pos()[0]/self.scale), round(pygame.mouse.get_pos()[1]/self.scale))
            self.scale += 1
            mouse_final = (round(pygame.mouse.get_pos()[0]/self.scale), round(pygame.mouse.get_pos()[1]/self.scale))
            mouse_offset = (mouse_final[0]-mouse_init[0], mouse_final[1]-mouse_init[1])
            self.offset = self.offset[0] - mouse_offset[0], self.offset[1] - mouse_offset[1]
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 5:
            try:
                mouse_init = (round(pygame.mouse.get_pos()[0]/self.scale), round(pygame.mouse.get_pos()[1]/self.scale))
                self.scale -= 1
                mouse_final = (round(pygame.mouse.get_pos()[0]/self.scale), round(pygame.mouse.get_pos()[1]/self.scale))
                mouse_offset = (mouse_final[0]-mouse_init[0], mouse_final[1]-mouse_init[1])
                self.offset = self.offset[0] - mouse_offset[0], self.offset[1] - mouse_offset[1]
            except ZeroDivisionError:
                self.scale += 1
        #elif event.type == pygame.KEYDOWN:
            #if event.key == pygame.K_LEFT:
                #self.offset = (self.offset[0]-1, self.offset[1])
            #elif event.key == pygame.K_RIGHT:
                #self.offset = (self.offset[0]+1, self.offset[1])
            #elif event.key == pygame.K_UP:
                #self.offset = (self.offset[0], self.offset[1]-1)
            #elif event.key == pygame.K_DOWN:
                #self.offset = (self.offset[0], self.offset[1]+1)
                
    def on_loop(self):
        for stitch in list(Stitch.stitches.values()):
            stitch.cycle
            stitch.check_neighbors()
            stitch.progress()
        #time.sleep(0.1)

    def on_render(self):
        self.screen.fill((255, 255, 255))
        for stitch in list(Stitch.stitches.values()):
            stitch.render(self, self.offset, self.scale)
        #for x in range(100):
        #    for y in range(100):
                #pygame.draw.line(self.screen, (0,0,0), ((self.offset[0]-x)*self.scale,0), ((self.offset[0]-x)*self.scale,1000))
                #pygame.draw.line(self.screen, (0,0,0), (0,(self.offset[1]-y)*self.scale), (1000,(self.offset[1]-y)*self.scale))
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
        
    def render(self, app, offset, scale):
        """
        Provide app object to this function so it can render to the active screen.
        offset is tuple of x,y offset between screen and world spaces.
        """

        if self.alive:
            # make the rectangle call more clear
            x, y = self.position 
            x_off, y_off = offset
            # (x, y, width, height)
            pygame.draw.rect(app.screen, (0, 0, 0), ((x-x_off)*scale, (y-y_off)*scale, scale, scale))
      
if __name__ == "__main__":
    myApp = App()
    myApp.on_execute()

    
