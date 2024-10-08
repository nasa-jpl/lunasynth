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
%GENERATECFAFIELD Creates and plots a randomly generated CFA rockfield over
%a given area
%   Command:
%   [rockField] = generateRockField(CFA,size_x,size_y,Hmin)
%
%   Inputs:
%   -	CFA: CFA value as a decimal (e.g. CFA5% would have an input of CFA=0.05)
%   -   size_x: x-dimension of rock field to be created, in meters (default value is 200)
%   -   size_y: y-dimension of rock field to be created, in meters (default value is 200)
%   -   Hmin: the smallest rock height you want to plot in meters (default value is 0.05)
%
%   Outputs:
%   -   rockField is a MATLAB structure capturing all rocks within the rockfield. This structure contains the following fields:
%       o   xv: x coordinates of rocks in the rock field
%       o   yv: y coordinates of rocks in the rock field
%       o   sizes: diameters of rocks in the rock field
%       o   heights: heights of rocks in the rock field
%       o   size_x: input x-dimension of rock field
%       o   size_y: input y-dimension of rock field
%       o   CFA: a vector of the cumulative contribution of each rock to the total CFA of the rock field (not important for your purposes)
%
%   Examples:
%   -   Command to generate a 6% 200x200 meter rockfield: generateRockField(0.06,200,200);
%   -   Command to generate a 5% 100x100 meter rockfield with a figure where the minimum size rock plotted is 5cm tall and all rocks >=25cm tall are plotted as a red circle: generateRockfield(0.06,200,200,0.05,0.25);
%

function rockField = generateRockField(k, size_x, size_y,Dmin)
    % create the full rock field
    RNGSeed = rng;
    D = logspace(log10(Dmin),log10(5),1000);
    N = NumPDF(D, k);

    NumCDF = cumsum(N(1:end-1).*diff(D));
    NumCDF = NumCDF/NumCDF(end);

    max_index = find(diff(NumCDF) < 1e-14);
    if ~isempty(max_index)

        D = D(1:max_index+1);
        NumCDF = NumCDF(1:max_index);

    end

    q =  0.5648 + 0.01285/k; % Experimental values Moon
    
    F = griddedInterpolant(NumCDF,D(1:end-1));
    NumRandNums = 6000*size_x*size_y/1000;
    dia = [];
    neededCFA = k*exp(-q*Dmin); % find the CFA which matches the min diameter
    computed_CFA = 0;
    while computed_CFA(end) < neededCFA % to make sure enough random rocks are generated
        randomNumbers = rand(NumRandNums,1);
        dia = [dia; F(randomNumbers)];
        computed_CFA = cumsum(pi/4*dia.^2)/(size_x*size_y);
    end

    computed_CFA = computed_CFA(computed_CFA <= neededCFA);
    ind = length(computed_CFA);
    dia = dia(1:ind); % diameters
    heights = D2H(dia); % heights
    rng(RNGSeed); % reset the rng for repeatable results
    rng(floor(1e6*rand(1,1)));

    xv = rand(ind,1)*size_x;
    yv = rand(ind,1)*size_y;

    rockField.xv = xv;
    rockField.yv = yv;
    rockField.sizes = dia;
    rockField.heights = heights;
    rockField.size_x = size_x;
    rockField.size_y = size_y;
    rockField.CFA = computed_CFA;
end

function N = NumPDF(D, k)
    % Probability distribution by number of rocks
    % k = cumulative fraction covered by rocks of all sizes
    % Source = http://onlinelibrary.wiley.com/doi/10.1029/96JE03319/pdf
    % Derived from Golombek 1997 by division by D^2
    P = AreaPDF(D, k);
    N = P ./ (D.^2)*4/pi;
end

function P=AreaPDF(D, k)
    % Probability distribution by areal coverage
    % k = cumulative fraction covered by rocks of all sizes
    % Source = http://onlinelibrary.wiley.com/doi/10.1029/96JE03319/pdf
    % Derived from Golombek 1997
    q =  0.5648 + 0.01285/k;    % Moon Values - Experimental
    P = k*q*exp(-q.*D);
end

function H=D2H(D)
    % Height to Diameter conversion
    H = D*0.5;
end

