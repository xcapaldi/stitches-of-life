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

    def on_event(self, event):
        if event.type == pygame.QUIT:
            self.running = False

    def on_loop(self):
        pass

    def on_render(self):
        pygame.draw.rect(self.screen, (255, 0, 0), (10,10,100,100))
        pygame.draw.rect(self.screen, (0, 255, 0), (150,10,100,100))
        pygame.draw.rect(self.screen, (0, 0, 255), (50, 150,100,100))
        pygame.draw.rect(self.screen, (100, 150, 0), (300, 300, 100,100))
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

if __name__ == "__main__":
    myApp = App()
    myApp.on_execute()

    
