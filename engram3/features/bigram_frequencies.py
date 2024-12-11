# features/bigram_frequencies.py
"""
English language bigrams and bigram frequencies

The ngram data below come from Peter Norvig's table: http://www.norvig.com/mayzner.html
"""

import numpy as np

onegrams = ['e', 't', 'a', 'o', 'i', 'n', 's', 'r', 'h', 'l', 'd', 'c', 'u',
            'm', 'f', 'p', 'g', 'w', 'y', 'b', 'v', 'k', 'x', 'j', 'q', 'z']
    
onegram_frequencies_array = np.array([0.12492063, 0.09275565, 0.08040605, 0.07640693, 
            0.07569278, 0.07233629, 0.06512767, 0.06279421, 0.05053301, 0.04068986,
            0.03816958, 0.03343774, 0.02729702, 0.02511761, 0.02403123, 0.02135891, 
            0.01869376, 0.01675664, 0.0166498 , 0.01484649, 0.01053252, 0.00540513, 
            0.00234857, 0.00158774, 0.00120469, 0.00089951])

onegram_frequencies = dict(zip(onegrams, onegram_frequencies_array))

bigrams = [bigram.lower() for bigram in [
       'TH', 'HE', 'IN', 'ER', 'AN', 'RE', 'ON', 'AT', 'EN', 'ND', 'TI',
       'ES', 'OR', 'TE', 'OF', 'ED', 'IS', 'IT', 'AL', 'AR', 'ST', 'TO',
       'NT', 'NG', 'SE', 'HA', 'AS', 'OU', 'IO', 'LE', 'VE', 'CO', 'ME',
       'DE', 'HI', 'RI', 'RO', 'IC', 'NE', 'EA', 'RA', 'CE', 'LI', 'CH',
       'LL', 'BE', 'MA', 'SI', 'OM', 'UR', 'CA', 'EL', 'TA', 'LA', 'NS',
       'DI', 'FO', 'HO', 'PE', 'EC', 'PR', 'NO', 'CT', 'US', 'AC', 'OT',
       'IL', 'TR', 'LY', 'NC', 'ET', 'UT', 'SS', 'SO', 'RS', 'UN', 'LO',
       'WA', 'GE', 'IE', 'WH', 'EE', 'WI', 'EM', 'AD', 'OL', 'RT', 'PO',
       'WE', 'NA', 'UL', 'NI', 'TS', 'MO', 'OW', 'PA', 'IM', 'MI', 'AI',
       'SH', 'IR', 'SU', 'ID', 'OS', 'IV', 'IA', 'AM', 'FI', 'CI', 'VI',
       'PL', 'IG', 'TU', 'EV', 'LD', 'RY', 'MP', 'FE', 'BL', 'AB', 'GH',
       'TY', 'OP', 'WO', 'SA', 'AY', 'EX', 'KE', 'FR', 'OO', 'AV', 'AG',
       'IF', 'AP', 'GR', 'OD', 'BO', 'SP', 'RD', 'DO', 'UC', 'BU', 'EI',
       'OV', 'BY', 'RM', 'EP', 'TT', 'OC', 'FA', 'EF', 'CU', 'RN', 'SC',
       'GI', 'DA', 'YO', 'CR', 'CL', 'DU', 'GA', 'QU', 'UE', 'FF', 'BA',
       'EY', 'LS', 'VA', 'UM', 'PP', 'UA', 'UP', 'LU', 'GO', 'HT', 'RU',
       'UG', 'DS', 'LT', 'PI', 'RC', 'RR', 'EG', 'AU', 'CK', 'EW', 'MU',
       'BR', 'BI', 'PT', 'AK', 'PU', 'UI', 'RG', 'IB', 'TL', 'NY', 'KI',
       'RK', 'YS', 'OB', 'MM', 'FU', 'PH', 'OG', 'MS', 'YE', 'UD', 'MB',
       'IP', 'UB', 'OI', 'RL', 'GU', 'DR', 'HR', 'CC', 'TW', 'FT', 'WN',
       'NU', 'AF', 'HU', 'NN', 'EO', 'VO', 'RV', 'NF', 'XP', 'GN', 'SM',
       'FL', 'IZ', 'OK', 'NL', 'MY', 'GL', 'AW', 'JU', 'OA', 'EQ', 'SY',
       'SL', 'PS', 'JO', 'LF', 'NV', 'JE', 'NK', 'KN', 'GS', 'DY', 'HY',
       'ZE', 'KS', 'XT', 'BS', 'IK', 'DD', 'CY', 'RP', 'SK', 'XI', 'OE',
       'OY', 'WS', 'LV', 'DL', 'RF', 'EU', 'DG', 'WR', 'XA', 'YI', 'NM',
       'EB', 'RB', 'TM', 'XC', 'EH', 'TC', 'GY', 'JA', 'HN', 'YP', 'ZA',
       'GG', 'YM', 'SW', 'BJ', 'LM', 'CS', 'II', 'IX', 'XE', 'OH', 'LK',
       'DV', 'LP', 'AX', 'OX', 'UF', 'DM', 'IU', 'SF', 'BT', 'KA', 'YT',
       'EK', 'PM', 'YA', 'GT', 'WL', 'RH', 'YL', 'HS', 'AH', 'YC', 'YN',
       'RW', 'HM', 'LW', 'HL', 'AE', 'ZI', 'AZ', 'LC', 'PY', 'AJ', 'IQ',
       'NJ', 'BB', 'NH', 'UO', 'KL', 'LR', 'TN', 'GM', 'SN', 'NR', 'FY',
       'MN', 'DW', 'SB', 'YR', 'DN', 'SQ', 'ZO', 'OJ', 'YD', 'LB', 'WT',
       'LG', 'KO', 'NP', 'SR', 'NQ', 'KY', 'LN', 'NW', 'TF', 'FS', 'CQ',
       'DH', 'SD', 'VY', 'DJ', 'HW', 'XU', 'AO', 'ML', 'UK', 'UY', 'EJ',
       'EZ', 'HB', 'NZ', 'NB', 'MC', 'YB', 'TP', 'XH', 'UX', 'TZ', 'BV',
       'MF', 'WD', 'OZ', 'YW', 'KH', 'GD', 'BM', 'MR', 'KU', 'UV', 'DT',
       'HD', 'AA', 'XX', 'DF', 'DB', 'JI', 'KR', 'XO', 'CM', 'ZZ', 'NX',
       'YG', 'XY', 'KG', 'TB', 'DC', 'BD', 'SG', 'WY', 'ZY', 'AQ', 'HF',
       'CD', 'VU', 'KW', 'ZU', 'BN', 'IH', 'TG', 'XV', 'UZ', 'BC', 'XF',
       'YZ', 'KM', 'DP', 'LH', 'WF', 'KF', 'PF', 'CF', 'MT', 'YU', 'CP',
       'PB', 'TD', 'ZL', 'SV', 'HC', 'MG', 'PW', 'GF', 'PD', 'PN', 'PC',
       'RX', 'TV', 'IJ', 'WM', 'UH', 'WK', 'WB', 'BH', 'OQ', 'KT', 'RQ',
       'KB', 'CG', 'VR', 'CN', 'PK', 'UU', 'YF', 'WP', 'CZ', 'KP', 'DQ',
       'WU', 'FM', 'WC', 'MD', 'KD', 'ZH', 'GW', 'RZ', 'CB', 'IW', 'XL',
       'HP', 'MW', 'VS', 'FC', 'RJ', 'BP', 'MH', 'HH', 'YH', 'UJ', 'FG',
       'FD', 'GB', 'PG', 'TK', 'KK', 'HQ', 'FN', 'LZ', 'VL', 'GP', 'HZ',
       'DK', 'YK', 'QI', 'LX', 'VD', 'ZS', 'BW', 'XQ', 'MV', 'UW', 'HG',
       'FB', 'SJ', 'WW', 'GK', 'UQ', 'BG', 'SZ', 'JR', 'QL', 'ZT', 'HK',
       'VC', 'XM', 'GC', 'FW', 'PZ', 'KC', 'HV', 'XW', 'ZW', 'FP', 'IY',
       'PV', 'VT', 'JP', 'CV', 'ZB', 'VP', 'ZR', 'FH', 'YV', 'ZG', 'ZM',
       'ZV', 'QS', 'KV', 'VN', 'ZN', 'QA', 'YX', 'JN', 'BF', 'MK', 'CW',
       'JM', 'LQ', 'JH', 'KJ', 'JC', 'GZ', 'JS', 'TX', 'FK', 'JL', 'VM',
       'LJ', 'TJ', 'JJ', 'CJ', 'VG', 'MJ', 'JT', 'PJ', 'WG', 'VH', 'BK',
       'VV', 'JD', 'TQ', 'VB', 'JF', 'DZ', 'XB', 'JB', 'ZC', 'FJ', 'YY',
       'QN', 'XS', 'QR', 'JK', 'JV', 'QQ', 'XN', 'VF', 'PX', 'ZD', 'QT',
       'ZP', 'QO', 'DX', 'HJ', 'GV', 'JW', 'QC', 'JY', 'GJ', 'QB', 'PQ',
       'JG', 'BZ', 'MX', 'QM', 'MZ', 'QF', 'WJ', 'ZQ', 'XR', 'ZK', 'CX',
       'FX', 'FV', 'BX', 'VW', 'VJ', 'MQ', 'QV', 'ZF', 'QE', 'YJ', 'GX',
       'KX', 'XG', 'QD', 'XJ', 'SX', 'VZ', 'VX', 'WV', 'YQ', 'BQ', 'GQ',
       'VK', 'ZJ', 'XK', 'QP', 'HX', 'FZ', 'QH', 'QJ', 'JZ', 'VQ', 'KQ',
       'XD', 'QW', 'JX', 'QX', 'KZ', 'WX', 'FQ', 'XZ', 'ZX']]

bigram_frequencies_array = np.array([
       3.55620339e-02, 3.07474124e-02, 2.43274529e-02, 2.04826481e-02,
       1.98515108e-02, 1.85432319e-02, 1.75804642e-02, 1.48673230e-02,
       1.45424846e-02, 1.35228145e-02, 1.34257882e-02, 1.33939375e-02,
       1.27653906e-02, 1.20486963e-02, 1.17497528e-02, 1.16812337e-02,
       1.12842988e-02, 1.12327374e-02, 1.08744953e-02, 1.07489847e-02,
       1.05347566e-02, 1.04126653e-02, 1.04125115e-02, 9.53014842e-03,
       9.32114579e-03, 9.25763559e-03, 8.71095073e-03, 8.70002319e-03,
       8.34931851e-03, 8.29254235e-03, 8.25280566e-03, 7.93859725e-03,
       7.93006486e-03, 7.64818391e-03, 7.63241814e-03, 7.27618866e-03,
       7.26724441e-03, 6.98707488e-03, 6.91722265e-03, 6.88165290e-03,
       6.85633031e-03, 6.51417363e-03, 6.24352184e-03, 5.97765978e-03,
       5.76571076e-03, 5.76283716e-03, 5.65269345e-03, 5.50057242e-03,
       5.46256885e-03, 5.42747781e-03, 5.38164098e-03, 5.30301559e-03,
       5.29886071e-03, 5.27529444e-03, 5.08937452e-03, 4.92966405e-03,
       4.87753568e-03, 4.84902069e-03, 4.77989185e-03, 4.77282719e-03,
       4.74470916e-03, 4.64574958e-03, 4.60971757e-03, 4.54257059e-03,
       4.47772200e-03, 4.42103298e-03, 4.31534618e-03, 4.25820178e-03,
       4.25013516e-03, 4.15745843e-03, 4.12608242e-03, 4.05151268e-03,
       4.05075209e-03, 3.97732158e-03, 3.96527277e-03, 3.94413046e-03,
       3.86884200e-03, 3.85337077e-03, 3.85189513e-03, 3.84646388e-03,
       3.78793431e-03, 3.77605408e-03, 3.74420703e-03, 3.73663638e-03,
       3.67956418e-03, 3.65492648e-03, 3.61676413e-03, 3.61373182e-03,
       3.60899233e-03, 3.47234973e-03, 3.45829494e-03, 3.39212478e-03,
       3.37488213e-03, 3.36877623e-03, 3.30478042e-03, 3.23572471e-03,
       3.17759946e-03, 3.17691369e-03, 3.16447752e-03, 3.15240004e-03,
       3.15172398e-03, 3.11176534e-03, 2.95503911e-03, 2.89966768e-03,
       2.87848219e-03, 2.86282435e-03, 2.84865969e-03, 2.84585627e-03,
       2.81484803e-03, 2.69544349e-03, 2.62987083e-03, 2.54961380e-03,
       2.54906719e-03, 2.54783715e-03, 2.52606379e-03, 2.47740122e-03,
       2.39175226e-03, 2.36573195e-03, 2.33400171e-03, 2.29786417e-03,
       2.27503360e-03, 2.27277101e-03, 2.23911052e-03, 2.21754315e-03,
       2.18017446e-03, 2.17360835e-03, 2.14044590e-03, 2.13767970e-03,
       2.13188615e-03, 2.10259217e-03, 2.04932647e-03, 2.04724906e-03,
       2.03256516e-03, 2.02845908e-03, 1.96777866e-03, 1.95449429e-03,
       1.95410531e-03, 1.91254221e-03, 1.89316385e-03, 1.88234971e-03,
       1.87652262e-03, 1.84944194e-03, 1.83351654e-03, 1.78086545e-03,
       1.76468430e-03, 1.75132925e-03, 1.71573739e-03, 1.70683303e-03,
       1.66405086e-03, 1.63999785e-03, 1.62732115e-03, 1.62613977e-03,
       1.60361051e-03, 1.54749379e-03, 1.51636562e-03, 1.51067364e-03,
       1.49901610e-03, 1.49455831e-03, 1.49011351e-03, 1.48460771e-03,
       1.48077067e-03, 1.47541326e-03, 1.47480347e-03, 1.46316579e-03,
       1.46204465e-03, 1.43745726e-03, 1.41513491e-03, 1.39980075e-03,
       1.38382616e-03, 1.36545598e-03, 1.36333253e-03, 1.36012483e-03,
       1.35189358e-03, 1.32127808e-03, 1.30185876e-03, 1.28328757e-03,
       1.27907576e-03, 1.26260675e-03, 1.23637099e-03, 1.23094105e-03,
       1.21386641e-03, 1.20743055e-03, 1.19536134e-03, 1.19032774e-03,
       1.17626124e-03, 1.16805780e-03, 1.14618533e-03, 1.11559852e-03,
       1.06597119e-03, 1.05782134e-03, 1.04699320e-03, 1.04540205e-03,
       1.01153313e-03, 9.97734501e-04, 9.86028683e-04, 9.84491816e-04,
       9.79174450e-04, 9.78784303e-04, 9.70343472e-04, 9.68322624e-04,
       9.66708177e-04, 9.60690121e-04, 9.59749105e-04, 9.43900197e-04,
       9.40242103e-04, 9.28331656e-04, 9.26685761e-04, 9.14014864e-04,
       9.02555222e-04, 8.92112065e-04, 8.85803335e-04, 8.77507468e-04,
       8.62646840e-04, 8.57695087e-04, 8.54499050e-04, 8.43925356e-04,
       8.31382851e-04, 8.23722323e-04, 8.16643644e-04, 7.89875969e-04,
       7.86444549e-04, 7.42072946e-04, 7.36927617e-04, 7.27646949e-04,
       7.25004577e-04, 7.11071849e-04, 6.92833068e-04, 6.71807283e-04,
       6.68638321e-04, 6.56391013e-04, 6.51990243e-04, 6.49048818e-04,
       6.43397537e-04, 6.43118050e-04, 6.37839069e-04, 6.21864133e-04,
       6.06367626e-04, 5.99162639e-04, 5.87024289e-04, 5.74860663e-04,
       5.72519573e-04, 5.68447140e-04, 5.58806800e-04, 5.45711864e-04,
       5.37896691e-04, 5.34768852e-04, 5.20071483e-04, 5.18874875e-04,
       5.16054649e-04, 5.14388309e-04, 5.11931727e-04, 5.04227393e-04,
       5.00890900e-04, 4.97325634e-04, 4.75088970e-04, 4.66605249e-04,
       4.58324041e-04, 4.29127437e-04, 4.27514542e-04, 4.17186146e-04,
       4.16199437e-04, 3.94646924e-04, 3.94183167e-04, 3.86306652e-04,
       3.61812839e-04, 3.50841120e-04, 3.49059129e-04, 3.23402665e-04,
       3.22604151e-04, 3.11527347e-04, 3.10032877e-04, 3.07611603e-04,
       2.96010489e-04, 2.88197255e-04, 2.77494857e-04, 2.70735751e-04,
       2.67122244e-04, 2.64790886e-04, 2.64597695e-04, 2.63237166e-04,
       2.61362824e-04, 2.59399816e-04, 2.58614910e-04, 2.57579773e-04,
       2.49143242e-04, 2.49036616e-04, 2.47547306e-04, 2.36748821e-04,
       2.35282013e-04, 2.32245156e-04, 2.30209194e-04, 2.28229670e-04,
       2.27822992e-04, 2.20319919e-04, 2.17945603e-04, 2.13543715e-04,
       1.97145202e-04, 1.90526970e-04, 1.90304866e-04, 1.88393786e-04,
       1.85754127e-04, 1.85322815e-04, 1.81767370e-04, 1.74089940e-04,
       1.71644610e-04, 1.71039222e-04, 1.69557657e-04, 1.66839046e-04,
       1.64718022e-04, 1.59561636e-04, 1.57658164e-04, 1.54026397e-04,
       1.52211752e-04, 1.51115808e-04, 1.47564559e-04, 1.46841709e-04,
       1.36432949e-04, 1.35005671e-04, 1.32141796e-04, 1.27573620e-04,
       1.27432415e-04, 1.26388914e-04, 1.25919175e-04, 1.23965197e-04,
       1.21174483e-04, 1.18691292e-04, 1.18219114e-04, 1.17637524e-04,
       1.17526303e-04, 1.13037594e-04, 1.10863960e-04, 1.09331046e-04,
       1.08837112e-04, 1.06567401e-04, 1.05698197e-04, 1.00512685e-04,
       1.00106518e-04, 9.85814937e-05, 9.17495595e-05, 9.15174736e-05,
       9.09807382e-05, 8.79007001e-05, 8.16240791e-05, 7.91627682e-05,
       7.79158645e-05, 7.56940333e-05, 7.44394656e-05, 7.18101849e-05,
       6.97589276e-05, 6.81802488e-05, 6.69029567e-05, 6.54143249e-05,
       6.08786925e-05, 6.07607969e-05, 6.03570614e-05, 5.98994801e-05,
       5.95001291e-05, 5.94970869e-05, 5.86983574e-05, 5.79700512e-05,
       5.66119466e-05, 5.50952209e-05, 5.47453912e-05, 5.43839597e-05,
       5.25861529e-05, 4.89722417e-05, 4.78187439e-05, 4.77415865e-05,
       4.77107257e-05, 4.62616737e-05, 4.60653783e-05, 4.60409299e-05,
       4.56730211e-05, 4.54645078e-05, 4.52324283e-05, 4.38982745e-05,
       4.36906610e-05, 4.33593810e-05, 4.31226640e-05, 4.29912118e-05,
       4.29446346e-05, 4.17137339e-05, 3.93478837e-05, 3.84895449e-05,
       3.84390172e-05, 3.81834469e-05, 3.53827628e-05, 3.47222349e-05,
       3.37168917e-05, 3.18518637e-05, 3.15951703e-05, 3.12905207e-05,
       3.10605585e-05, 3.02567524e-05, 2.91709879e-05, 2.89567711e-05,
       2.85652293e-05, 2.82994071e-05, 2.80417376e-05, 2.77861205e-05,
       2.77303518e-05, 2.76273746e-05, 2.72172235e-05, 2.69880432e-05,
       2.66503046e-05, 2.66033916e-05, 2.62086568e-05, 2.59259584e-05,
       2.57640153e-05, 2.56299050e-05, 2.54449453e-05, 2.51909823e-05,
       2.47409597e-05, 2.46797892e-05, 2.42472084e-05, 2.35748710e-05,
       2.24438116e-05, 2.24317329e-05, 2.23097275e-05, 2.21249597e-05,
       2.17815183e-05, 2.15248592e-05, 2.09465192e-05, 2.09125513e-05,
       1.96913177e-05, 1.95330853e-05, 1.91064697e-05, 1.88952009e-05,
       1.85746459e-05, 1.81220081e-05, 1.78919334e-05, 1.73267658e-05,
       1.61874055e-05, 1.60765855e-05, 1.58740992e-05, 1.45486411e-05,
       1.40812264e-05, 1.36678429e-05, 1.32768479e-05, 1.31460479e-05,
       1.30872012e-05, 1.29588223e-05, 1.25748548e-05, 1.24146066e-05,
       1.22821602e-05, 1.22486357e-05, 1.20714645e-05, 1.20448925e-05,
       1.19866728e-05, 1.18936663e-05, 1.17590888e-05, 1.17001978e-05,
       1.16346360e-05, 1.11092945e-05, 1.08992577e-05, 1.06740258e-05,
       1.06735218e-05, 1.06144296e-05, 1.05679067e-05, 1.03656570e-05,
       1.03317955e-05, 9.98437559e-06, 9.01036943e-06, 8.85768061e-06,
       8.76035160e-06, 8.60019167e-06, 8.19227801e-06, 7.80479658e-06,
       7.53516931e-06, 7.44150882e-06, 7.30644125e-06, 7.26777599e-06,
       7.06747616e-06, 6.95177332e-06, 6.85925126e-06, 6.74132156e-06,
       6.71322068e-06, 6.70106994e-06, 6.66133186e-06, 6.47626505e-06,
       6.38130476e-06, 6.29576510e-06, 6.24612583e-06, 5.93271496e-06,
       5.92132104e-06, 5.83947722e-06, 5.76779879e-06, 5.76465728e-06,
       5.53187023e-06, 5.47131015e-06, 5.33180695e-06, 5.22417954e-06,
       5.20732008e-06, 5.15949060e-06, 5.11569104e-06, 4.95336950e-06,
       4.94557425e-06, 4.73636484e-06, 4.63955858e-06, 4.53340156e-06,
       4.22935422e-06, 4.19307790e-06, 4.17347414e-06, 4.12142146e-06,
       4.11855764e-06, 3.80541311e-06, 3.36707879e-06, 3.29563656e-06,
       3.17577578e-06, 3.05442971e-06, 2.98983688e-06, 2.97762691e-06,
       2.95066092e-06, 2.91720550e-06, 2.89840858e-06, 2.77497857e-06,
       2.76265227e-06, 2.74176112e-06, 2.70310579e-06, 2.61648976e-06,
       2.60275585e-06, 2.56616744e-06, 2.55465117e-06, 2.49712549e-06,
       2.42815484e-06, 2.37933375e-06, 2.35040476e-06, 2.33914845e-06,
       2.33036549e-06, 2.32978989e-06, 2.28930419e-06, 2.28804340e-06,
       2.26346210e-06, 2.24353844e-06, 2.23182640e-06, 2.23165865e-06,
       2.22696341e-06, 2.22115030e-06, 2.21572164e-06, 2.20668084e-06,
       2.19243658e-06, 2.17382266e-06, 2.08159887e-06, 2.07762818e-06,
       1.95415065e-06, 1.88693410e-06, 1.83219245e-06, 1.81431726e-06,
       1.67631850e-06, 1.67169206e-06, 1.63803449e-06, 1.57770706e-06,
       1.56577585e-06, 1.53130790e-06, 1.52519015e-06, 1.52439998e-06,
       1.49350905e-06, 1.47212210e-06, 1.45715861e-06, 1.40331777e-06,
       1.38641504e-06, 1.29786439e-06, 1.27069447e-06, 1.25613209e-06,
       1.23105569e-06, 1.22268909e-06, 1.21688094e-06, 1.18065108e-06,
       1.18060143e-06, 1.16794389e-06, 1.13216621e-06, 1.12716419e-06,
       1.12418866e-06, 1.12412659e-06, 1.05684621e-06, 1.05049722e-06,
       1.04986594e-06, 1.03676402e-06, 1.03482230e-06, 9.96847192e-07,
       9.75926251e-07, 9.54397081e-07, 9.36101632e-07, 9.30100914e-07,
       9.27467975e-07, 8.92801774e-07, 8.85217179e-07, 8.58891337e-07,
       7.80484800e-07, 7.67724409e-07, 7.54031637e-07, 7.45052550e-07,
       7.32511689e-07, 7.06828122e-07, 6.59585949e-07, 6.40055245e-07,
       6.18628925e-07, 6.17142222e-07, 6.09904832e-07, 6.07242457e-07,
       5.72270900e-07, 5.49823535e-07, 5.22568859e-07, 5.01838721e-07,
       4.91372576e-07, 4.82981856e-07, 4.69688423e-07, 4.59727658e-07,
       4.54795508e-07, 4.22875379e-07, 4.13494116e-07, 3.99834682e-07,
       3.97288987e-07, 3.87644926e-07, 3.84245584e-07, 3.81268632e-07,
       3.67029696e-07, 3.57267536e-07, 3.52642869e-07, 3.51058992e-07,
       3.44112772e-07, 3.36167495e-07, 3.24215712e-07, 3.23810344e-07,
       3.21814716e-07, 3.21505459e-07, 3.10936465e-07, 2.88018831e-07,
       2.86309762e-07, 2.76140106e-07, 2.63218703e-07, 2.56899508e-07,
       2.51244222e-07, 2.25386521e-07, 2.15766576e-07, 2.03018243e-07,
       1.99078411e-07, 1.97551987e-07, 1.96981706e-07, 1.92415912e-07,
       1.84391194e-07, 1.81253585e-07, 1.78663913e-07, 1.77747846e-07,
       1.59541769e-07, 1.38003378e-07, 1.36499298e-07, 1.22889160e-07,
       1.22576357e-07, 1.19711121e-07, 1.09597855e-07, 9.97477409e-08,
       9.65292710e-08, 9.36271510e-08, 9.35785637e-08, 9.34540807e-08,
       8.40270671e-08, 7.82629028e-08, 7.54898762e-08, 6.64058115e-08,
       5.96748649e-08, 5.79118882e-08, 5.73650143e-08, 5.65688198e-08,
       5.34673852e-08, 5.34237630e-08, 5.29956976e-08, 4.84174907e-08,
       3.83818937e-08])

bigram_frequencies = {bigram: freq for bigram, freq in zip(bigrams, bigram_frequencies_array)}

"""
print(bigram_frequencies)
{'th': 0.0355620339, 'he': 0.0307474124, 'in': 0.0243274529, 'er': 0.0204826481, 'an': 0.0198515108, 're': 0.0185432319, 'on': 0.0175804642, 'at': 0.014867323, 'en': 0.0145424846, 'nd': 0.0135228145, 'ti': 0.0134257882, 'es': 0.0133939375, 'or': 0.0127653906, 'te': 0.0120486963, 'of': 0.0117497528, 'ed': 0.0116812337, 'is': 0.0112842988, 'it': 0.0112327374, 'al': 0.0108744953, 'ar': 0.0107489847, 'st': 0.0105347566, 'to': 0.0104126653, 'nt': 0.0104125115, 'ng': 0.00953014842, 'se': 0.00932114579, 'ha': 0.00925763559, 'as': 0.00871095073, 'ou': 0.00870002319, 'io': 0.00834931851, 'le': 0.00829254235, 've': 0.00825280566, 'co': 0.00793859725, 'me': 0.00793006486, 'de': 0.00764818391, 'hi': 0.00763241814, 'ri': 0.00727618866, 'ro': 0.00726724441, 'ic': 0.00698707488, 'ne': 0.00691722265, 'ea': 0.0068816529, 'ra': 0.00685633031, 'ce': 0.00651417363, 'li': 0.00624352184, 'ch': 0.00597765978, 'll': 0.00576571076, 'be': 0.00576283716, 'ma': 0.00565269345, 'si': 0.00550057242, 'om': 0.00546256885, 'ur': 0.00542747781, 'ca': 0.00538164098, 'el': 0.00530301559, 'ta': 0.00529886071, 'la': 0.00527529444, 'ns': 0.00508937452, 'di': 0.00492966405, 'fo': 0.00487753568, 'ho': 0.00484902069, 'pe': 0.00477989185, 'ec': 0.00477282719, 'pr': 0.00474470916, 'no': 0.00464574958, 'ct': 0.00460971757, 'us': 0.00454257059, 'ac': 0.004477722, 'ot': 0.00442103298, 'il': 0.00431534618, 'tr': 0.00425820178, 'ly': 0.00425013516, 'nc': 0.00415745843, 'et': 0.00412608242, 'ut': 0.00405151268, 'ss': 0.00405075209, 'so': 0.00397732158, 'rs': 0.00396527277, 'un': 0.00394413046, 'lo': 0.003868842, 'wa': 0.00385337077, 'ge': 0.00385189513, 'ie': 0.00384646388, 'wh': 0.00378793431, 'ee': 0.00377605408, 'wi': 0.00374420703, 'em': 0.00373663638, 'ad': 0.00367956418, 'ol': 0.00365492648, 'rt': 0.00361676413, 'po': 0.00361373182, 'we': 0.00360899233, 'na': 0.00347234973, 'ul': 0.00345829494, 'ni': 0.00339212478, 'ts': 0.00337488213, 'mo': 0.00336877623, 'ow': 0.00330478042, 'pa': 0.00323572471, 'im': 0.00317759946, 'mi': 0.00317691369, 'ai': 0.00316447752, 'sh': 0.00315240004, 'ir': 0.00315172398, 'su': 0.00311176534, 'id': 0.00295503911, 'os': 0.00289966768, 'iv': 0.00287848219, 'ia': 0.00286282435, 'am': 0.00284865969, 'fi': 0.00284585627, 'ci': 0.00281484803, 'vi': 0.00269544349, 'pl': 0.00262987083, 'ig': 0.0025496138, 'tu': 0.00254906719, 'ev': 0.00254783715, 'ld': 0.00252606379, 'ry': 0.00247740122, 'mp': 0.00239175226, 'fe': 0.00236573195, 'bl': 0.00233400171, 'ab': 0.00229786417, 'gh': 0.0022750336, 'ty': 0.00227277101, 'op': 0.00223911052, 'wo': 0.00221754315, 'sa': 0.00218017446, 'ay': 0.00217360835, 'ex': 0.0021404459, 'ke': 0.0021376797, 'fr': 0.00213188615, 'oo': 0.00210259217, 'av': 0.00204932647, 'ag': 0.00204724906, 'if': 0.00203256516, 'ap': 0.00202845908, 'gr': 0.00196777866, 'od': 0.00195449429, 'bo': 0.00195410531, 'sp': 0.00191254221, 'rd': 0.00189316385, 'do': 0.00188234971, 'uc': 0.00187652262, 'bu': 0.00184944194, 'ei': 0.00183351654, 'ov': 0.00178086545, 'by': 0.0017646843, 'rm': 0.00175132925, 'ep': 0.00171573739, 'tt': 0.00170683303, 'oc': 0.00166405086, 'fa': 0.00163999785, 'ef': 0.00162732115, 'cu': 0.00162613977, 'rn': 0.00160361051, 'sc': 0.00154749379, 'gi': 0.00151636562, 'da': 0.00151067364, 'yo': 0.0014990161, 'cr': 0.00149455831, 'cl': 0.00149011351, 'du': 0.00148460771, 'ga': 0.00148077067, 'qu': 0.00147541326, 'ue': 0.00147480347, 'ff': 0.00146316579, 'ba': 0.00146204465, 'ey': 0.00143745726, 'ls': 0.00141513491, 'va': 0.00139980075, 'um': 0.00138382616, 'pp': 0.00136545598, 'ua': 0.00136333253, 'up': 0.00136012483, 'lu': 0.00135189358, 'go': 0.00132127808, 'ht': 0.00130185876, 'ru': 0.00128328757, 'ug': 0.00127907576, 'ds': 0.00126260675, 'lt': 0.00123637099, 'pi': 0.00123094105, 'rc': 0.00121386641, 'rr': 0.00120743055, 'eg': 0.00119536134, 'au': 0.00119032774, 'ck': 0.00117626124, 'ew': 0.0011680578, 'mu': 0.00114618533, 'br': 0.00111559852, 'bi': 0.00106597119, 'pt': 0.00105782134, 'ak': 0.0010469932, 'pu': 0.00104540205, 'ui': 0.00101153313, 'rg': 0.000997734501, 'ib': 0.000986028683, 'tl': 0.000984491816, 'ny': 0.00097917445, 'ki': 0.000978784303, 'rk': 0.000970343472, 'ys': 0.000968322624, 'ob': 0.000966708177, 'mm': 0.000960690121, 'fu': 0.000959749105, 'ph': 0.000943900197, 'og': 0.000940242103, 'ms': 0.000928331656, 'ye': 0.000926685761, 'ud': 0.000914014864, 'mb': 0.000902555222, 'ip': 0.000892112065, 'ub': 0.000885803335, 'oi': 0.000877507468, 'rl': 0.00086264684, 'gu': 0.000857695087, 'dr': 0.00085449905, 'hr': 0.000843925356, 'cc': 0.000831382851, 'tw': 0.000823722323, 'ft': 0.000816643644, 'wn': 0.000789875969, 'nu': 0.000786444549, 'af': 0.000742072946, 'hu': 0.000736927617, 'nn': 0.000727646949, 'eo': 0.000725004577, 'vo': 0.000711071849, 'rv': 0.000692833068, 'nf': 0.000671807283, 'xp': 0.000668638321, 'gn': 0.000656391013, 'sm': 0.000651990243, 'fl': 0.000649048818, 'iz': 0.000643397537, 'ok': 0.00064311805, 'nl': 0.000637839069, 'my': 0.000621864133, 'gl': 0.000606367626, 'aw': 0.000599162639, 'ju': 0.000587024289, 'oa': 0.000574860663, 'eq': 0.000572519573, 'sy': 0.00056844714, 'sl': 0.0005588068, 'ps': 0.000545711864, 'jo': 0.000537896691, 'lf': 0.000534768852, 'nv': 0.000520071483, 'je': 0.000518874875, 'nk': 0.000516054649, 'kn': 0.000514388309, 'gs': 0.000511931727, 'dy': 0.000504227393, 'hy': 0.0005008909, 'ze': 0.000497325634, 'ks': 0.00047508897, 'xt': 0.000466605249, 'bs': 0.000458324041, 'ik': 0.000429127437, 'dd': 0.000427514542, 'cy': 0.000417186146, 'rp': 0.000416199437, 'sk': 0.000394646924, 'xi': 0.000394183167, 'oe': 0.000386306652, 'oy': 0.000361812839, 'ws': 0.00035084112, 'lv': 0.000349059129, 'dl': 0.000323402665, 'rf': 0.000322604151, 'eu': 0.000311527347, 'dg': 0.000310032877, 'wr': 0.000307611603, 'xa': 0.000296010489, 'yi': 0.000288197255, 'nm': 0.000277494857, 'eb': 0.000270735751, 'rb': 0.000267122244, 'tm': 0.000264790886, 'xc': 0.000264597695, 'eh': 0.000263237166, 'tc': 0.000261362824, 'gy': 0.000259399816, 'ja': 0.00025861491, 'hn': 0.000257579773, 'yp': 0.000249143242, 'za': 0.000249036616, 'gg': 0.000247547306, 'ym': 0.000236748821, 'sw': 0.000235282013, 'bj': 0.000232245156, 'lm': 0.000230209194, 'cs': 0.00022822967, 'ii': 0.000227822992, 'ix': 0.000220319919, 'xe': 0.000217945603, 'oh': 0.000213543715, 'lk': 0.000197145202, 'dv': 0.00019052697, 'lp': 0.000190304866, 'ax': 0.000188393786, 'ox': 0.000185754127, 'uf': 0.000185322815, 'dm': 0.00018176737, 'iu': 0.00017408994, 'sf': 0.00017164461, 'bt': 0.000171039222, 'ka': 0.000169557657, 'yt': 0.000166839046, 'ek': 0.000164718022, 'pm': 0.000159561636, 'ya': 0.000157658164, 'gt': 0.000154026397, 'wl': 0.000152211752, 'rh': 0.000151115808, 'yl': 0.000147564559, 'hs': 0.000146841709, 'ah': 0.000136432949, 'yc': 0.000135005671, 'yn': 0.000132141796, 'rw': 0.00012757362, 'hm': 0.000127432415, 'lw': 0.000126388914, 'hl': 0.000125919175, 'ae': 0.000123965197, 'zi': 0.000121174483, 'az': 0.000118691292, 'lc': 0.000118219114, 'py': 0.000117637524, 'aj': 0.000117526303, 'iq': 0.000113037594, 'nj': 0.00011086396, 'bb': 0.000109331046, 'nh': 0.000108837112, 'uo': 0.000106567401, 'kl': 0.000105698197, 'lr': 0.000100512685, 'tn': 0.000100106518, 'gm': 9.85814937e-05, 'sn': 9.17495595e-05, 'nr': 9.15174736e-05, 'fy': 9.09807382e-05, 'mn': 8.79007001e-05, 'dw': 8.16240791e-05, 'sb': 7.91627682e-05, 'yr': 7.79158645e-05, 'dn': 7.56940333e-05, 'sq': 7.44394656e-05, 'zo': 7.18101849e-05, 'oj': 6.97589276e-05, 'yd': 6.81802488e-05, 'lb': 6.69029567e-05, 'wt': 6.54143249e-05, 'lg': 6.08786925e-05, 'ko': 6.07607969e-05, 'np': 6.03570614e-05, 'sr': 5.98994801e-05, 'nq': 5.95001291e-05, 'ky': 5.94970869e-05, 'ln': 5.86983574e-05, 'nw': 5.79700512e-05, 'tf': 5.66119466e-05, 'fs': 5.50952209e-05, 'cq': 5.47453912e-05, 'dh': 5.43839597e-05, 'sd': 5.25861529e-05, 'vy': 4.89722417e-05, 'dj': 4.78187439e-05, 'hw': 4.77415865e-05, 'xu': 4.77107257e-05, 'ao': 4.62616737e-05, 'ml': 4.60653783e-05, 'uk': 4.60409299e-05, 'uy': 4.56730211e-05, 'ej': 4.54645078e-05, 'ez': 4.52324283e-05, 'hb': 4.38982745e-05, 'nz': 4.3690661e-05, 'nb': 4.3359381e-05, 'mc': 4.3122664e-05, 'yb': 4.29912118e-05, 'tp': 4.29446346e-05, 'xh': 4.17137339e-05, 'ux': 3.93478837e-05, 'tz': 3.84895449e-05, 'bv': 3.84390172e-05, 'mf': 3.81834469e-05, 'wd': 3.53827628e-05, 'oz': 3.47222349e-05, 'yw': 3.37168917e-05, 'kh': 3.18518637e-05, 'gd': 3.15951703e-05, 'bm': 3.12905207e-05, 'mr': 3.10605585e-05, 'ku': 3.02567524e-05, 'uv': 2.91709879e-05, 'dt': 2.89567711e-05, 'hd': 2.85652293e-05, 'aa': 2.82994071e-05, 'xx': 2.80417376e-05, 'df': 2.77861205e-05, 'db': 2.77303518e-05, 'ji': 2.76273746e-05, 'kr': 2.72172235e-05, 'xo': 2.69880432e-05, 'cm': 2.66503046e-05, 'zz': 2.66033916e-05, 'nx': 2.62086568e-05, 'yg': 2.59259584e-05, 'xy': 2.57640153e-05, 'kg': 2.5629905e-05, 'tb': 2.54449453e-05, 'dc': 2.51909823e-05, 'bd': 2.47409597e-05, 'sg': 2.46797892e-05, 'wy': 2.42472084e-05, 'zy': 2.3574871e-05, 'aq': 2.24438116e-05, 'hf': 2.24317329e-05, 'cd': 2.23097275e-05, 'vu': 2.21249597e-05, 'kw': 2.17815183e-05, 'zu': 2.15248592e-05, 'bn': 2.09465192e-05, 'ih': 2.09125513e-05, 'tg': 1.96913177e-05, 'xv': 1.95330853e-05, 'uz': 1.91064697e-05, 'bc': 1.88952009e-05, 'xf': 1.85746459e-05, 'yz': 1.81220081e-05, 'km': 1.78919334e-05, 'dp': 1.73267658e-05, 'lh': 1.61874055e-05, 'wf': 1.60765855e-05, 'kf': 1.58740992e-05, 'pf': 1.45486411e-05, 'cf': 1.40812264e-05, 'mt': 1.36678429e-05, 'yu': 1.32768479e-05, 'cp': 1.31460479e-05, 'pb': 1.30872012e-05, 'td': 1.29588223e-05, 'zl': 1.25748548e-05, 'sv': 1.24146066e-05, 'hc': 1.22821602e-05, 'mg': 1.22486357e-05, 'pw': 1.20714645e-05, 'gf': 1.20448925e-05, 'pd': 1.19866728e-05, 'pn': 1.18936663e-05, 'pc': 1.17590888e-05, 'rx': 1.17001978e-05, 'tv': 1.1634636e-05, 'ij': 1.11092945e-05, 'wm': 1.08992577e-05, 'uh': 1.06740258e-05, 'wk': 1.06735218e-05, 'wb': 1.06144296e-05, 'bh': 1.05679067e-05, 'oq': 1.0365657e-05, 'kt': 1.03317955e-05, 'rq': 9.98437559e-06, 'kb': 9.01036943e-06, 'cg': 8.85768061e-06, 'vr': 8.7603516e-06, 'cn': 8.60019167e-06, 'pk': 8.19227801e-06, 'uu': 7.80479658e-06, 'yf': 7.53516931e-06, 'wp': 7.44150882e-06, 'cz': 7.30644125e-06, 'kp': 7.26777599e-06, 'dq': 7.06747616e-06, 'wu': 6.95177332e-06, 'fm': 6.85925126e-06, 'wc': 6.74132156e-06, 'md': 6.71322068e-06, 'kd': 6.70106994e-06, 'zh': 6.66133186e-06, 'gw': 6.47626505e-06, 'rz': 6.38130476e-06, 'cb': 6.2957651e-06, 'iw': 6.24612583e-06, 'xl': 5.93271496e-06, 'hp': 5.92132104e-06, 'mw': 5.83947722e-06, 'vs': 5.76779879e-06, 'fc': 5.76465728e-06, 'rj': 5.53187023e-06, 'bp': 5.47131015e-06, 'mh': 5.33180695e-06, 'hh': 5.22417954e-06, 'yh': 5.20732008e-06, 'uj': 5.1594906e-06, 'fg': 5.11569104e-06, 'fd': 4.9533695e-06, 'gb': 4.94557425e-06, 'pg': 4.73636484e-06, 'tk': 4.63955858e-06, 'kk': 4.53340156e-06, 'hq': 4.22935422e-06, 'fn': 4.1930779e-06, 'lz': 4.17347414e-06, 'vl': 4.12142146e-06, 'gp': 4.11855764e-06, 'hz': 3.80541311e-06, 'dk': 3.36707879e-06, 'yk': 3.29563656e-06, 'qi': 3.17577578e-06, 'lx': 3.05442971e-06, 'vd': 2.98983688e-06, 'zs': 2.97762691e-06, 'bw': 2.95066092e-06, 'xq': 2.9172055e-06, 'mv': 2.89840858e-06, 'uw': 2.77497857e-06, 'hg': 2.76265227e-06, 'fb': 2.74176112e-06, 'sj': 2.70310579e-06, 'ww': 2.61648976e-06, 'gk': 2.60275585e-06, 'uq': 2.56616744e-06, 'bg': 2.55465117e-06, 'sz': 2.49712549e-06, 'jr': 2.42815484e-06, 'ql': 2.37933375e-06, 'zt': 2.35040476e-06, 'hk': 2.33914845e-06, 'vc': 2.33036549e-06, 'xm': 2.32978989e-06, 'gc': 2.28930419e-06, 'fw': 2.2880434e-06, 'pz': 2.2634621e-06, 'kc': 2.24353844e-06, 'hv': 2.2318264e-06, 'xw': 2.23165865e-06, 'zw': 2.22696341e-06, 'fp': 2.2211503e-06, 'iy': 2.21572164e-06, 'pv': 2.20668084e-06, 'vt': 2.19243658e-06, 'jp': 2.17382266e-06, 'cv': 2.08159887e-06, 'zb': 2.07762818e-06, 'vp': 1.95415065e-06, 'zr': 1.8869341e-06, 'fh': 1.83219245e-06, 'yv': 1.81431726e-06, 'zg': 1.6763185e-06, 'zm': 1.67169206e-06, 'zv': 1.63803449e-06, 'qs': 1.57770706e-06, 'kv': 1.56577585e-06, 'vn': 1.5313079e-06, 'zn': 1.52519015e-06, 'qa': 1.52439998e-06, 'yx': 1.49350905e-06, 'jn': 1.4721221e-06, 'bf': 1.45715861e-06, 'mk': 1.40331777e-06, 'cw': 1.38641504e-06, 'jm': 1.29786439e-06, 'lq': 1.27069447e-06, 'jh': 1.25613209e-06, 'kj': 1.23105569e-06, 'jc': 1.22268909e-06, 'gz': 1.21688094e-06, 'js': 1.18065108e-06, 'tx': 1.18060143e-06, 'fk': 1.16794389e-06, 'jl': 1.13216621e-06, 'vm': 1.12716419e-06, 'lj': 1.12418866e-06, 'tj': 1.12412659e-06, 'jj': 1.05684621e-06, 'cj': 1.05049722e-06, 'vg': 1.04986594e-06, 'mj': 1.03676402e-06, 'jt': 1.0348223e-06, 'pj': 9.96847192e-07, 'wg': 9.75926251e-07, 'vh': 9.54397081e-07, 'bk': 9.36101632e-07, 'vv': 9.30100914e-07, 'jd': 9.27467975e-07, 'tq': 8.92801774e-07, 'vb': 8.85217179e-07, 'jf': 8.58891337e-07, 'dz': 7.804848e-07, 'xb': 7.67724409e-07, 'jb': 7.54031637e-07, 'zc': 7.4505255e-07, 'fj': 7.32511689e-07, 'yy': 7.06828122e-07, 'qn': 6.59585949e-07, 'xs': 6.40055245e-07, 'qr': 6.18628925e-07, 'jk': 6.17142222e-07, 'jv': 6.09904832e-07, 'qq': 6.07242457e-07, 'xn': 5.722709e-07, 'vf': 5.49823535e-07, 'px': 5.22568859e-07, 'zd': 5.01838721e-07, 'qt': 4.91372576e-07, 'zp': 4.82981856e-07, 'qo': 4.69688423e-07, 'dx': 4.59727658e-07, 'hj': 4.54795508e-07, 'gv': 4.22875379e-07, 'jw': 4.13494116e-07, 'qc': 3.99834682e-07, 'jy': 3.97288987e-07, 'gj': 3.87644926e-07, 'qb': 3.84245584e-07, 'pq': 3.81268632e-07, 'jg': 3.67029696e-07, 'bz': 3.57267536e-07, 'mx': 3.52642869e-07, 'qm': 3.51058992e-07, 'mz': 3.44112772e-07, 'qf': 3.36167495e-07, 'wj': 3.24215712e-07, 'zq': 3.23810344e-07, 'xr': 3.21814716e-07, 'zk': 3.21505459e-07, 'cx': 3.10936465e-07, 'fx': 2.88018831e-07, 'fv': 2.86309762e-07, 'bx': 2.76140106e-07, 'vw': 2.63218703e-07, 'vj': 2.56899508e-07, 'mq': 2.51244222e-07, 'qv': 2.25386521e-07, 'zf': 2.15766576e-07, 'qe': 2.03018243e-07, 'yj': 1.99078411e-07, 'gx': 1.97551987e-07, 'kx': 1.96981706e-07, 'xg': 1.92415912e-07, 'qd': 1.84391194e-07, 'xj': 1.81253585e-07, 'sx': 1.78663913e-07, 'vz': 1.77747846e-07, 'vx': 1.59541769e-07, 'wv': 1.38003378e-07, 'yq': 1.36499298e-07, 'bq': 1.2288916e-07, 'gq': 1.22576357e-07, 'vk': 1.19711121e-07, 'zj': 1.09597855e-07, 'xk': 9.97477409e-08, 'qp': 9.6529271e-08, 'hx': 9.3627151e-08, 'fz': 9.35785637e-08, 'qh': 9.34540807e-08, 'qj': 8.40270671e-08, 'jz': 7.82629028e-08, 'vq': 7.54898762e-08, 'kq': 6.64058115e-08, 'xd': 5.96748649e-08, 'qw': 5.79118882e-08, 'jx': 5.73650143e-08, 'qx': 5.65688198e-08, 'kz': 5.34673852e-08, 'wx': 5.3423763e-08, 'fq': 5.29956976e-08, 'xz': 4.84174907e-08, 'zx': 3.83818937e-08}
"""

