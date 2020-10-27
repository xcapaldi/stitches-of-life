#!/usr/bin/env python3

"""
In a knitted stitch:

* Wale - width of stitch * Course - height of stitch

The ratio of these is dependent on yarn weight, needle size and knitter.
It seems to fall between 1:1 and 1:1.85 (stitches:rows).
Maybe we will allow the user to define this.
"""


import pygame

class App:
    def __init__(self):
        self.running = True
        self.screen = None
        self.size = self.width, self.height = 640,400
        self.flags = None

    def on_init(self):
        pygame.init()
        self.screen = pygame.display.set_mode(self.size) #self.flags
        self.screen.fill((255, 255, 255))
        self.running = True
        for i in range(100):
            Stitch(i*10, i+20)
        print(Stitch.stitches)

    def on_event(self, event):
        if event.type == pygame.QUIT:
            self.running = False

    def on_loop(self):
        pass

    def on_render(self):
        for stitch in list(Stitch.stitches.values()):
            stitch.render(self)
        pygame.display.update()

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
        self.on_cleanup()

# we have two spaces
# screen space
# and world space
# world space is purely a collection of data in the world

class Stitch:
    stitches = {}
    def __init__(self, x, y):
        self.position = (x, y)
        self.alive = False
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

    def check_neighbors(self):
        self.live_neighbors = 0
        for neighbor in self.neighbors:
            if stitches[neighbor].alive:
                self.live_neighbors += 1

    def propogate(self):
        if self.live_neighbors == 3:
            self.alive = True
            print

    def live_or_die(self):
        if self.live_neighbors < 2:
            self.alive = False
            print(f"{self.position} died from solitude")
        elif self.live_neighbors > 3:
            self.alive = False
            print(f"{self.position} died from overcrowding")
        else:
            pass

    def progress(self):
        if self.alive:
            self.live_or_die()
        else:
            self.propogate()

    def delete(self):
        del Stitch.stitches[self.position]
        
    def render(self, app):
        """
        Provide app object to this function so it can render to the active screen.
        """

        # make the rectangle call more clear
        x, y = self.position 
        (x, y, width, height)
        pygame.draw.rect(app.screen, (255, 0, 0), (x, y, 10, 10))
        
if __name__ == "__main__":
    myApp = App()
    myApp.on_execute()

    
