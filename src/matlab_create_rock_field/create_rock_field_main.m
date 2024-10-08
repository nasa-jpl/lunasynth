%  Copyright (c) 2024. Jet Propulsion Laboratory. All rights reserved.
%
%  Licensed under the Apache License, Version 2.0 (the "License");
%  you may not use this file except in compliance with the License.
%  You may obtain a copy of the License at
%
%  https://www.apache.org/licenses/LICENSE-2.0
%
%  Unless required by applicable law or agreed to in writing, software
%  distributed under the License is distributed on an "AS IS" BASIS,
%  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
%  See the License for the specific language governing permissions and
%  limitations under the License.
%
%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%
%
%   Main function to generate a rock distribution
%   and prep the file for python.
%
%   @author: Daniel Posada, 2023 
%   NASA Jet Propulsion Laboratory, 347P
%
%
%   @comments: Based on the Mars CFA MATLAB tool
%   by Sydney Do. Modified it to add the Moon
%   parameters for the exponential distribution.
%
%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%% Prepare environment to run a clean slate
clear all; close all; clc;

%% Define parameters for SRL and SRH distribution
%   Where the inputs are: 
%   -	CFA: CFA value as a decimal (e.g. CFA5% would have an input of CFA=0.05)
%   -   size_x: x-dimension of rock field to be created, in meters (default value is 200)
%   -   size_y: y-dimension of rock field to be created, in meters (default value is 200)
%   -   Dmin: the smallest rock height you want to plot in meters (default value is 0.05)

% Size of Area to populate

CFA = 0.5;
size_x = 50;
size_y = 50;
Dmin = 0.2;

[rockField] = generateRockField(CFA, size_x, size_y, Dmin);
plotRockField(rockField)

%% Clean variable to save array that can be loaded in Blender:
fields = {'size_x', 'size_y', 'CFA'};
rock_field_clean = rmfield(rockField, fields);
rock_field_array = table2array(struct2table(rock_field_clean));
num_rocks = numel(rock_field_array(:,1));

% Random assignments
rock_type = randi([1, 20], num_rocks, 1);  % Shape type for each rock
rot_x = 2 * pi * rand(num_rocks, 1);       % Rotation about X-axis in radians
rot_y = 2 * pi * rand(num_rocks, 1);       % Rotation about Y-axis in radians
rot_z = 2 * pi * rand(num_rocks, 1);       % Rotation about Z-axis in radians
z_shift = 0.4 * rand(num_rocks, 1) - 0.2;  % Z-shift from -0.2 to +0.2

% Offset to center distribution around 0,0
offset = [(size_x/2)*ones(num_rocks,1) (size_y/2)*ones(num_rocks,1) ...
    zeros(num_rocks,1) zeros(num_rocks,1)];

% [x y size height rock_type roll pitch yaw depth]
rock_field_array_output = [rock_field_array-offset rock_type rot_x rot_y rot_z z_shift];

writematrix(rock_field_array_output,'rockField.csv');

function []=plotRockField(rockField)
    xv = rockField.xv;
    yv = rockField.yv;
    sizes = rockField.sizes;
    
    figure('Name',"Rock Field")
    scatter(xv,yv, sizes)
    xlabel('x [m]')
    ylabel('y [m]')
    axis equal
    
    figure('Name',"Sizes Histogram")
    hist(sizes)
    xlabel('Size [m]')
    ylabel('Number of rocks')
end
