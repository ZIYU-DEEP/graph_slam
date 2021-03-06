from slam_parameters import *
from core.initialize import graph_slam_initialize
from core.linearize import graph_slam_linearize
from core.reduce import graph_slam_reduce
from core.solve import graph_slam_solve
from utils.map_generator import generate_ground_truth_map
from utils.measurement_model import generate_measurements
from utils.path_generator import generate_ground_truth_path
from utils.plot_utils import plot_path, plot_measurements_for_state

import matplotlib.pyplot as plt
import numpy as np

import random as rnd
from typing import List


class GraphSlamState(object):
    def __init__(self):
        self.ground_truth_map = np.empty((0, 0))
        self.landmarks = []

        self.ground_truth_states = []
        self.controls = []

        self.measurements = []

        self.initial_state_estimates = []

        self.true_random_gen = rnd.SystemRandom()


def generate_unique_correspondences_for_measurements(measurements: List[List[np.ndarray]]) -> List[List[int]]:
    correspondence_index = 0
    correspondences = []

    for measurements_for_state in measurements:
        correspondences.append([index + correspondence_index for index, _ in enumerate(measurements_for_state)])
        correspondence_index = correspondence_index + len(measurements_for_state)

    return correspondences


def transform_states_into_frame(states: List[np.ndarray], frame: np.ndarray):
    frame_orientation = frame[2]
    sinfr = math.sin(frame_orientation)
    cosfr = math.cos(frame_orientation)

    for state_index, state in enumerate(states):
        new_x = frame[0] + state[0] * cosfr - state[1] * sinfr
        state[1] = frame[1] + state[0] * sinfr + state[1] * cosfr
        state[0] = new_x
        state[2] = state[2] + frame_orientation

        states[state_index] = state


def graph_slam_random_map():
    ground_truth_map, landmarks = generate_ground_truth_map(MAP_HEIGHT, MAP_WIDTH, LANDMARK_COUNT)

    # Set up truly random number generation for creating the ground truth path (if the system supports it)
    true_random_gen = rnd.SystemRandom()
    rnd.seed(true_random_gen.random())

    ground_truth_states, controls = \
        generate_ground_truth_path(ground_truth_map, max_velocity=MAX_VELOCITY,
                                   velocity_deviation=VELOCITY_DEVIATION, max_turn_rate=MAX_TURN_RATE,
                                   turn_rate_deviation=TURN_RATE_DEVIATION, step_count=STEP_COUNT,
                                   velocity_control_deviation=VELOCITY_CONTROL_DEVIATION,
                                   turn_rate_control_deviation=TURN_RATE_CONTROL_DEVIATION)

    measurements, correspondences = generate_measurements(
        ground_truth_states, landmarks, max_sensing_range=MAX_SENSING_RANGE,
        sensing_range_deviation=SENSING_RANGE_DEVIATION, distance_deviation=DISTANCE_DEVIATION,
        heading_deviation=HEADING_DEVIATION)

    initial_state_estimates = graph_slam_initialize(controls, state_t0=np.array([[0, 0, 0]]).T)

    landmark_estimates = dict()
    state_estimates = initial_state_estimates

    correspondences = generate_unique_correspondences_for_measurements(measurements)

    R = np.identity(3) * 0.00001
    Q = np.identity(3) * 0.00001

    for iteration_index in range(25):
        xi, omega, landmark_estimates = \
            graph_slam_linearize(state_estimates=state_estimates, landmark_estimates=landmark_estimates,
                                 controls=controls, measurements=measurements, correspondences=correspondences,
                                 motion_error_covariance=R, measurement_noise_covariance=Q)

        xi_reduced, omega_reduced = graph_slam_reduce(xi, omega, landmark_estimates)
        state_estimates, sigma_states, landmark_estimates = graph_slam_solve(xi_reduced, omega_reduced, xi, omega)

    transform_states_into_frame(state_estimates, ground_truth_states[0])
    transform_states_into_frame(initial_state_estimates, ground_truth_states[0])

    plt.figure(figsize=[10, 5])
    plt.subplot(131)
    plt.title("Ground truth map")
    plt.imshow(ground_truth_map, origin='lower')

    plot_path(ground_truth_states, 'C0', "Ground truth")
    plot_path(initial_state_estimates, 'C1', "Initial estimate with odometry")
    plot_path(state_estimates, 'C2', "Estimate after optimization")

    plt.legend()

    current_state = 1
    plot_measurements_for_state(ground_truth_states[current_state], measurements[current_state])

    plt.subplot(132)
    plt.title("Information matrix")
    omega_binary = omega != 0
    plt.imshow(omega_binary)

    plt.subplot(133)
    plt.title("Reduced information matrix")
    omega_reduced_binary = omega_reduced != 0
    plt.imshow(omega_reduced_binary)

    plt.show()


if __name__ == "__main__":
    graph_slam_random_map()
