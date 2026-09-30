
 
def find_solutions(initial_angle, goal_angle_list, filename):
    
    if initial_angle > 65535 or initial_angle < 0 or isinstance(initial_angle, int) == False:
        print('Error: The initial angle is not a valid input')
    
    with open(filename, "a") as file:
    
        Solution_Found = False
        for i in range(8192):
            for angle in goal_angle_list:
                if (initial_angle + i*1800)%65536 == angle:
                    Solution_Found = True
                    print("%d = %s is a working initial angle with %d Left ESS turns for goal angle %d = %s" %(initial_angle, hex(initial_angle), i, angle, hex(angle)))
                    file.write("%d = %s is a working initial angle with %d Left ESS turns for goal angle %d = %s\n" %(initial_angle, hex(initial_angle), i, angle, hex(angle)))
                    
                if (initial_angle - i*1800)%65536 == angle:
                    Solution_Found = True
                    print("%d = %s is a working initial angle with %d Right ESS turns for goal angle %d = %s" %(initial_angle, hex(initial_angle), i, angle, hex(angle)))
                    file.write("%d = %s is a working initial angle with %d Right ESS turns for goal angle %d = %s\n" %(initial_angle, hex(initial_angle), i, angle, hex(angle)))
                    
        if Solution_Found == False:
            print("No solutions were found for this initial angle.")
 
 
def sortFirst(val): 
    return val[0]  
 
def find_ranked_solutions(initial_angle_list, goal_angle_list, filename, max_deku_spins=0, sort_by_deku_spins=True):
    
    #solution_dict = {}
    solution_list = []
    
    with open(filename, "a") as file:
    
        for initial_angle in initial_angle_list:
            
            print(hex(initial_angle))
            
            if initial_angle > 65535 or initial_angle < 0 or isinstance(initial_angle, int) == False:
                print('Error: The initial angle is not a valid input')
            
            for n_deku_spins in range(max_deku_spins+1):
                
                #initial_angle = (initial_angle - 0x1E0*n_deku_spins) % 0x10000
                test_angle = (initial_angle - 0x1E0*n_deku_spins) % 0x10000
            
                Solution_Found = False
                for i in range(8192):
                    for angle in goal_angle_list:
                        
                        #if (initial_angle, angle) not in solution_dict:
                         #   solution_dict[(initial_angle, angle, 'left')] = []
                          #  solution_dict[(initial_angle, angle, 'right')] = []
                        
                        if (test_angle + i*1800)%65536 == angle:
                            Solution_Found = True
                            #print("%d = %s is a working initial angle with %d Left ESS turns for goal angle %d = %s" %(initial_angle, hex(initial_angle), i, angle, hex(angle)))
                            #solution_dict[(initial_angle, angle, 'left')].append(i)
                            solution_list.append((i, initial_angle, angle, 'Left', n_deku_spins))
                            #file.write("%d = %s is a working initial angle with %d Left ESS turns for goal angle %d = %s\n" %(initial_angle, hex(initial_angle), i, angle, hex(angle)))
                            
                        if (test_angle - i*1800)%65536 == angle:
                            Solution_Found = True
                            #print("%d = %s is a working initial angle with %d Right ESS turns for goal angle %d = %s" %(initial_angle, hex(initial_angle), i, angle, hex(angle)))
                            #solution_dict[(initial_angle, angle, 'right')].append(i)
                            solution_list.append((i, initial_angle, angle, 'Right', n_deku_spins))
                            #file.write("%d = %s is a working initial angle with %d Right ESS turns for goal angle %d = %s\n" %(initial_angle, hex(initial_angle), i, angle, hex(angle)))
                            
                #if Solution_Found == False:
                    #print("No solutions were found for this initial angle.")
        
        ##### Now sort and then write to file
        
        
        #solution_list.sort(key=sortFirst)
        if sort_by_deku_spins == True:
            solution_list.sort(key=lambda element: (element[4], element[0]))
        else:
            solution_list.sort(key=lambda element: (element[0], element[4]))
        
        for entry in solution_list:
            
            file.write("%d = %s is a working initial angle with %d %s ESS turns and %d Deku Spins for goal angle %d = %s\n" %(entry[1], hex(entry[1]), entry[0], entry[3], entry[4], entry[2], hex(entry[2])))
            
        print("Done.")



def get_initial_angle_list(angle, cam):
    return [angle, cam, (cam+0x4000)%0x10000, (cam+0x8000)%0x10000, (cam+0xC000)%0x10000]


#angle = 0xFF2F#0xCDE1#0xAD28#0xFF2F
#cam_angle = 0xFFE3#0xCDE5#0xAD2D#0xFFE3


#angle = 0x68EB
#cam_angle = 0x68A8

angle = 0x0000#0xc000#0xfe86#0xf811#0x9259#0xA6F9#0xAACE#0xA339#0x68EB#0x6937
cam_angle = 0x0000#0xc001#0xff61#0xf89c#0x92a2#0xA6FB#0xAACC#0xA33A#0x68A8 #0x68FB



initial_angle_list = get_initial_angle_list(angle, cam_angle) + [0, 0x4000, 0x8000, 0xC000]

cam_angles = [0xF064, 0xF064, 0x3E49, 0x7097] #[0xb900, 0xb1fe, 0xaaec, 0xa3ea, 0x9cd9, 0x95d7, 0x8ef5, 0x87df, 0x80ef, 0x7a06, 0x72b9, 0x6b9a, 0x646d, 0x5d56, 0x5637, 0x4f84, 0x4872, 0x4170]#[0xc624, 0xcc3f, 0xd366, 0xdac6, 0xe236, 0xe9cd, 0xf15d, 0xf8f8, 0x6d, 0x7c5, 0xef8, 0x1613, 0x1cf7, 0x23cb, 0x297a, 0x308c]#[0x127, 0x803d, 0x4000, 0xbe31, 0xbc50, 0xba70, 0xb890]#[0x8219, 0xe1, 0x40e0, 0xc0d1, 0x8119, 0xfefc, 0xfd05, 0x824, 0xf5d, 0x1669, 0x1d69, 0x23a1, 0x2a3a, 0x313c, 0xe85e, 0xf988, 0xf221, 0xeaa3, 0xe33a, 0xdbcf, 0xd40e, 0xcdf7]#[0x697, 0xdd6, 0x14e8, 0x1bee, 0x222c, 0x28ba, 0x2fbc, 0x36ce] + [0xf7f3, 0xf089, 0xe90c, 0xe1a6] + [0x6b, 0xc001, 0x8046, 0xfd69]#[0xf923, 0x38ae, 0xb8a0, 0x78ed, 0xf6a1]#[0xfff8, 0x73d, 0xe6a, 0x158a, 0x1c7d, 0x22c8, 0x294a, 0x305c, 0x375e] + [0xf122, 0xe9b5, 0xe23d, 0xdae4, 0xd323, 0xcd21, 0xc6d3, 0xc001, 0xb8d0, 0xb1ce]#[0x8b88, 0x846a, 0x8098, 0x767d, 0x6f37, 0x67e1, 0x60a2, 0x595d, 0x52a8, 0x4b97, 0x4501] + [0x99c4, 0xa069, 0xa77b, 0xae7d, 0xb58f, 0xbc91, 0xc392, 0xca94, 0xd10b, 0xd73e, 0xde5c, 0xe64a, 0xedb5, 0xf50e, 0xfc71, 0x3a4, 0xae7, 0x1203, 0x1887, 0x1f6c, 0x2609, 0x2d0b, 0x341d]#[0xae0d, 0xb50f, 0xbc20, 0xc312, 0xca23, 0xd08e, 0xd6ce, 0xddda, 0xe5d5, 0xed2e, 0xf499, 0xfbeb, 0x330, 0xa63, 0x1191, 0x1898, 0x1efe, 0x2589, 0x2c9b, 0x339d]#[0x9ff9, 0x9943, 0x9231, 0x8b38, 0x843b, 0x8098, 0x7609, 0x6eb2, 0x676d, 0x601d, 0x58ea, 0x5227, 0x4b27, 0x4481]#[0xA3CA, 0x9CB8, 0x960C, 0x8EE5, 0x87EA, 0x812B, 0x7A40, 0x72A9, 0x6B62, 0x640F, 0x5CD5, 0x5597, 0x4EF6, 0x47EB, 0x4150]#[0xB1DE, 0xB8E0, 0xC001, 0xC6E3, 0xCDF5, 0xD447, 0xDAA0, 0xE200, 0xE9D5, 0xF130, 0xF897, 0xFFE4, 0x71F]#[0x7224, 0x6ACC, 0x638A, 0x5C40, 0x5514, 0x4E65, 0x476C, 0x40C0]#[0x9c38, 0x957A, 0x8E63, 0x8754, 0x80A9, 0x7979, 0xAA4C, 0xB14E, 0xB85F, 0xC001, 0xC663, 0xCD65, 0xD3C9, 0xDA0F, 0xE17C, 0xE93E, 0xF0A9, 0xF800, 0xFF5F, 0x68B]
for a in cam_angles:
    l = get_initial_angle_list(a, a)
    initial_angle_list += l

print(f"len(initial_angle_list)={len(initial_angle_list)}, initial_angle_list={initial_angle_list}")

#goal_angle_list = list(range(0x400, 0x410))
#goal_angle_list = list(range(0x4C0, 0x4D0))
#goal_angle_list = list(range(0x420, 0x430))
#goal_angle_list = list(range(0x460, 0x470))
goal_angle_list = list(range(0xff90, 0xffa0))
failed_angles = []#[0x462]
for failed_angle in failed_angles:
    if failed_angle in goal_angle_list:
        goal_angle_list.remove(failed_angle)



complete_name = 'angle_solutions.txt'
find_ranked_solutions(initial_angle_list, goal_angle_list, complete_name, max_deku_spins=10, sort_by_deku_spins=False)








