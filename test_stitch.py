#!/usr/bin/env python3

"""
Unit tests for Stitches of Life - Conway's Game of Life implementation
"""

import pytest
import pygame
from stitch import Stitch, App
import stitch


class TestStitchInitialization:
    """Test Stitch class initialization"""

    def setup_method(self):
        """Clear stitches dictionary before each test"""
        Stitch.stitches = {}

    def test_stitch_creation(self):
        """Test that a stitch can be created with correct position"""
        stitch = Stitch(5, 10)
        assert stitch.position == (5, 10)
        assert stitch.alive == False
        assert stitch.vital == False
        assert stitch.neighbors == []

    def test_stitch_added_to_class_dict(self):
        """Test that created stitches are added to the class dictionary"""
        stitch1 = Stitch(0, 0)
        stitch2 = Stitch(1, 1)

        assert (0, 0) in Stitch.stitches
        assert (1, 1) in Stitch.stitches
        assert Stitch.stitches[(0, 0)] == stitch1
        assert Stitch.stitches[(1, 1)] == stitch2

    def test_multiple_stitches_same_position(self):
        """Test that creating a stitch at the same position overwrites previous"""
        stitch1 = Stitch(5, 5)
        stitch1.alive = True
        stitch2 = Stitch(5, 5)

        assert Stitch.stitches[(5, 5)] == stitch2
        assert stitch2.alive == False


class TestFindNeighbors:
    """Test the find_neighbors method"""

    def setup_method(self):
        """Clear stitches dictionary before each test"""
        Stitch.stitches = {}

    def test_find_neighbors_center_cell(self):
        """Test finding neighbors for a cell in the center of a grid"""
        # Create a 3x3 grid
        for x in range(3):
            for y in range(3):
                Stitch(x, y)

        # Center stitch should have 8 neighbors
        center = Stitch.stitches[(1, 1)]
        center.find_neighbors()

        assert len(center.neighbors) == 8
        expected_neighbors = [
            (0, 0), (1, 0), (2, 0),
            (0, 1),         (2, 1),
            (0, 2), (1, 2), (2, 2)
        ]
        assert set(center.neighbors) == set(expected_neighbors)

    def test_find_neighbors_corner_cell(self):
        """Test finding neighbors for a corner cell"""
        # Create a 3x3 grid
        for x in range(3):
            for y in range(3):
                Stitch(x, y)

        # Corner stitch should have 3 neighbors (boundary)
        corner = Stitch.stitches[(0, 0)]
        corner.find_neighbors()

        assert len(corner.neighbors) == 3
        expected_neighbors = [(1, 0), (0, 1), (1, 1)]
        assert set(corner.neighbors) == set(expected_neighbors)

    def test_find_neighbors_edge_cell(self):
        """Test finding neighbors for an edge cell"""
        # Create a 3x3 grid
        for x in range(3):
            for y in range(3):
                Stitch(x, y)

        # Edge stitch should have 5 neighbors
        edge = Stitch.stitches[(1, 0)]
        edge.find_neighbors()

        assert len(edge.neighbors) == 5
        expected_neighbors = [(0, 0), (2, 0), (0, 1), (1, 1), (2, 1)]
        assert set(edge.neighbors) == set(expected_neighbors)

    def test_find_neighbors_excludes_self(self):
        """Test that a stitch doesn't include itself as a neighbor"""
        # Create a 3x3 grid
        for x in range(3):
            for y in range(3):
                Stitch(x, y)

        stitch = Stitch.stitches[(1, 1)]
        stitch.find_neighbors()

        assert stitch.position not in stitch.neighbors


class TestCheckNeighbors:
    """Test the check_neighbors method"""

    def setup_method(self):
        """Clear stitches dictionary before each test"""
        Stitch.stitches = {}

    def test_check_neighbors_none_alive(self):
        """Test counting neighbors when none are alive"""
        # Create a 3x3 grid
        for x in range(3):
            for y in range(3):
                Stitch(x, y)

        center = Stitch.stitches[(1, 1)]
        center.find_neighbors()
        center.check_neighbors()

        assert center.live_neighbors == 0

    def test_check_neighbors_all_alive(self):
        """Test counting neighbors when all are alive"""
        # Create a 3x3 grid and make all alive
        for x in range(3):
            for y in range(3):
                stitch = Stitch(x, y)
                stitch.alive = True

        center = Stitch.stitches[(1, 1)]
        center.find_neighbors()
        center.check_neighbors()

        assert center.live_neighbors == 8

    def test_check_neighbors_some_alive(self):
        """Test counting neighbors when some are alive"""
        # Create a 3x3 grid
        for x in range(3):
            for y in range(3):
                Stitch(x, y)

        # Make 3 neighbors alive
        Stitch.stitches[(0, 0)].alive = True
        Stitch.stitches[(1, 0)].alive = True
        Stitch.stitches[(2, 0)].alive = True

        center = Stitch.stitches[(1, 1)]
        center.find_neighbors()
        center.check_neighbors()

        assert center.live_neighbors == 3


class TestGameOfLifeRules:
    """Test Conway's Game of Life rules"""

    def setup_method(self):
        """Clear stitches dictionary before each test"""
        Stitch.stitches = {}

    def test_live_or_die_underpopulation(self):
        """Test that alive cells with fewer than 2 neighbors die"""
        stitch = Stitch(5, 5)
        stitch.alive = True
        stitch.live_neighbors = 1
        stitch.live_or_die()

        assert stitch.vital == False

    def test_live_or_die_survival_two_neighbors(self):
        """Test that alive cells with 2 neighbors survive"""
        stitch = Stitch(5, 5)
        stitch.alive = True
        stitch.live_neighbors = 2
        stitch.live_or_die()

        assert stitch.vital == True

    def test_live_or_die_survival_three_neighbors(self):
        """Test that alive cells with 3 neighbors survive"""
        stitch = Stitch(5, 5)
        stitch.alive = True
        stitch.live_neighbors = 3
        stitch.live_or_die()

        assert stitch.vital == True

    def test_live_or_die_overpopulation(self):
        """Test that alive cells with more than 3 neighbors die"""
        stitch = Stitch(5, 5)
        stitch.alive = True
        stitch.live_neighbors = 4
        stitch.live_or_die()

        assert stitch.vital == False

    def test_propogate_reproduction(self):
        """Test that dead cells with exactly 3 neighbors come to life"""
        stitch = Stitch(5, 5)
        stitch.alive = False
        stitch.live_neighbors = 3
        stitch.propogate()

        assert stitch.vital == True

    def test_propogate_no_reproduction(self):
        """Test that dead cells without 3 neighbors stay dead"""
        stitch = Stitch(5, 5)
        stitch.alive = False
        stitch.vital = False
        stitch.live_neighbors = 2
        stitch.propogate()

        assert stitch.vital == False


class TestProgressAndCycle:
    """Test progress and cycle methods"""

    def setup_method(self):
        """Clear stitches dictionary before each test"""
        Stitch.stitches = {}

    def test_progress_alive_cell(self):
        """Test that progress calls live_or_die for alive cells"""
        stitch = Stitch(5, 5)
        stitch.alive = True
        stitch.live_neighbors = 2
        stitch.progress()

        assert stitch.vital == True

    def test_progress_dead_cell(self):
        """Test that progress calls propogate for dead cells"""
        stitch = Stitch(5, 5)
        stitch.alive = False
        stitch.live_neighbors = 3
        stitch.progress()

        assert stitch.vital == True

    def test_cycle_updates_alive_state(self):
        """Test that cycle updates alive state from vital"""
        stitch = Stitch(5, 5)
        stitch.alive = False
        stitch.vital = True
        stitch.cycle()

        assert stitch.alive == True

        stitch.vital = False
        stitch.cycle()

        assert stitch.alive == False


class TestStitchDelete:
    """Test stitch deletion"""

    def setup_method(self):
        """Clear stitches dictionary before each test"""
        Stitch.stitches = {}

    def test_delete_stitch(self):
        """Test that a stitch can be deleted from the class dictionary"""
        stitch = Stitch(5, 5)
        assert (5, 5) in Stitch.stitches

        stitch.delete()
        assert (5, 5) not in Stitch.stitches


class TestGamePatterns:
    """Test known Game of Life patterns"""

    def setup_method(self):
        """Clear stitches dictionary before each test"""
        Stitch.stitches = {}

    def test_blinker_pattern(self):
        """Test the blinker oscillator pattern"""
        # Create a small grid
        for x in range(5):
            for y in range(5):
                Stitch(x, y)

        # Set up blinker (horizontal)
        Stitch.stitches[(1, 2)].alive = True
        Stitch.stitches[(2, 2)].alive = True
        Stitch.stitches[(3, 2)].alive = True

        # Find all neighbors
        for stitch in Stitch.stitches.values():
            stitch.find_neighbors()

        # Run one generation
        for stitch in Stitch.stitches.values():
            stitch.check_neighbors()
            stitch.progress()
        for stitch in Stitch.stitches.values():
            stitch.cycle()

        # Should now be vertical
        assert Stitch.stitches[(2, 1)].alive == True
        assert Stitch.stitches[(2, 2)].alive == True
        assert Stitch.stitches[(2, 3)].alive == True
        assert Stitch.stitches[(1, 2)].alive == False
        assert Stitch.stitches[(3, 2)].alive == False

    def test_block_pattern_static(self):
        """Test that a block (still life) remains static"""
        # Create a small grid
        for x in range(4):
            for y in range(4):
                Stitch(x, y)

        # Set up 2x2 block
        Stitch.stitches[(1, 1)].alive = True
        Stitch.stitches[(1, 2)].alive = True
        Stitch.stitches[(2, 1)].alive = True
        Stitch.stitches[(2, 2)].alive = True

        # Find all neighbors
        for stitch in Stitch.stitches.values():
            stitch.find_neighbors()

        # Run one generation
        for stitch in Stitch.stitches.values():
            stitch.check_neighbors()
            stitch.progress()
        for stitch in Stitch.stitches.values():
            stitch.cycle()

        # Block should remain unchanged
        assert Stitch.stitches[(1, 1)].alive == True
        assert Stitch.stitches[(1, 2)].alive == True
        assert Stitch.stitches[(2, 1)].alive == True
        assert Stitch.stitches[(2, 2)].alive == True


class TestSetupFunctions:
    """Test the setup helper functions"""

    def setup_method(self):
        """Clear stitches dictionary before each test"""
        Stitch.stitches = {}

    def test_full_setup(self):
        """Test that test_full_setup creates an n x n grid"""
        stitch.test_full_setup(10)

        # Should have 100 stitches
        assert len(Stitch.stitches) == 100

        # Check that all positions exist
        for x in range(10):
            for y in range(10):
                assert (x, y) in Stitch.stitches

    def test_glider_setup(self):
        """Test that test_glider creates the correct pattern"""
        stitch.test_glider()

        # Should have 100x100 grid
        assert len(Stitch.stitches) == 10000

        # Check glider positions
        assert Stitch.stitches[(11, 12)].alive == True
        assert Stitch.stitches[(12, 13)].alive == True
        assert Stitch.stitches[(13, 11)].alive == True
        assert Stitch.stitches[(13, 12)].alive == True
        assert Stitch.stitches[(13, 13)].alive == True

    def test_blinker_setup(self):
        """Test that test_blinker creates the correct pattern"""
        stitch.test_blinker()

        # Should have 100x100 grid
        assert len(Stitch.stitches) == 10000

        # Check blinker positions
        assert Stitch.stitches[(10, 10)].alive == True
        assert Stitch.stitches[(11, 10)].alive == True
        assert Stitch.stitches[(12, 10)].alive == True


class TestAppInitialization:
    """Test App class initialization"""

    def test_app_creation(self):
        """Test that App can be created with default values"""
        app = App()

        assert app.running == True
        assert app.screen == None
        assert app.width == 1000
        assert app.height == 1000
        assert app.offset == (0, 0)
        assert app.rmb == False
        assert app.scale == 10


class TestRender:
    """Test rendering functionality"""

    def setup_method(self):
        """Clear stitches dictionary and initialize pygame before each test"""
        Stitch.stitches = {}
        pygame.init()

    def teardown_method(self):
        """Clean up pygame after each test"""
        pygame.quit()

    def test_render_alive_stitch(self):
        """Test that alive stitches render correctly"""
        app = App()
        app.screen = pygame.display.set_mode((100, 100))

        stitch = Stitch(5, 5)
        stitch.alive = True

        # Should not raise an error
        stitch.render(app, (0, 0), 10)

    def test_render_dead_stitch(self):
        """Test that dead stitches don't render"""
        app = App()
        app.screen = pygame.display.set_mode((100, 100))

        stitch = Stitch(5, 5)
        stitch.alive = False

        # Should not raise an error
        stitch.render(app, (0, 0), 10)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
