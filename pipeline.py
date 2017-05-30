import numpy as np
import cv2
from math import sqrt


yROIpct = .6 # % in y axis to start ROI
minslope = .4
maxslope = 4

def canny(img, thres_low=30, thres_high=150, kernel_size=5):
    ''' Applies Canny transform after a Gaussian blur
    '''
    img = cv2.GaussianBlur(img, (kernel_size, kernel_size), 0)
    return cv2.Canny(img, thres_low, thres_high)
    
def mask_ROI(img):
    ''' Applies a ROI image mask. Regions outside the ROI is set to black.
    '''
    if len(img.shape) > 2:
        chs = img.shape[2]  # i.e. 3 or 4 depending on your image
        ignore_mask_color = (255,) * chs
    else:
        ignore_mask_color = 255
          
    xlen = img.shape[1]
    ylen = img.shape[0]
    xmid = xlen // 2
    y = int(ylen * yROIpct)
    xoffset = xlen // 30
    roi_coords = np.array([[(0,ylen),(xmid-xoffset, y), (xmid+xoffset, y),(xlen,ylen)]], dtype=np.int32)
    
    mask = np.zeros_like(img)   
    cv2.fillPoly(mask, roi_coords, ignore_mask_color)
    return cv2.bitwise_and(img, mask)

def draw_lines(image, lines, color=(255, 0, 0), thickness=5, multicolors=False):
    ''' Returns image with lines drawn with color and thickness.
    lines: list of (x1,y1,x2,y2) line coordinates
    '''
    colors = [(255,0,0),(0,255,0),(0,0,255),(255,255,0),(0,255,255),(255,0,255)] if multicolors else [color]
    result = np.copy(image)*0
    i = 0

    for line in lines:
        for x1,y1,x2,y2 in line:
            cv2.line(result, (x1, y1), (x2, y2), colors[i], thickness)
            if multicolors:
                i += 1
                i = i % len(colors)
    return result

def hough_lines(edges_img, rho=2, theta=np.pi/180, thres=16, 
    min_laneline_len=0, max_gap_btw_lines=0):
    ''' Returns list of line segment coordinates (x1,y1,x2,y2) from edges_img
    edges_img: output of a Canny transform.
    thres: min # of polar space intersections to be considered a line
    '''
    xlen = edges_img.shape[1]
    ylen = edges_img.shape[0]
    minlen = min_laneline_len or xlen * 0.02  # 19.2 on 960wd
    maxgap = max_gap_btw_lines or xlen * 0.013 # 12.5 on 960wd
    return cv2.HoughLinesP(edges_img, rho, theta, thres, np.array([]), minlen, maxgap)

def weighted_img(lines_img, initial_img, α=0.8, β=1., λ=0.):
    '''
    Returns initial_img * α + img * β + λ
    lines_img: is image with lines drawn on it
    initial_img: is image before any processing
    '''
    if len(initial_img.shape) == 2:
        # If img is a binary image (2 dims instead of 3), make it 3 dims
        initial_img = np.dstack((initial_img, initial_img, initial_img))
    return cv2.addWeighted(initial_img, α, lines_img, β, λ)

def lane_lines(line_segments, ylen, prvm=0, prvb=0, dbg=False, dbglines=False):
    ''' Returns list of [result lines, avg m, avg b (of y=mx+b)]
    where result lines are the 2 resulting left and right lanes

    line_segments: output from hough_lines()
    prvm, prvb: prv m, prv b (of y=mx+b)
    dbg: print verbose info if True
    dbglines: add input lines to result lines if True
    '''
    lrMs = [[], []] # left and right line m's
    lrBs = [[], []] # left and right line b's 
    lrWs = [[], []] # left and right line weights
    result = [] # lane lines 
    yclip = int(ylen*yROIpct)

    for segment in line_segments:
        for x1,y1,x2,y2 in segment:
            if x2 - x1 == 0:
                break
            m = (y2 - y1)/(x2 - x1)
            b = y1 - m*x1
            wt = sqrt((x2-x1)**2 + (y2-y1)**2)
            iside = -1
                
            if -maxslope < m < -minslope:
                iside = 0
            elif minslope < m < maxslope:
                iside = 1
            else:
                pass
            if iside >= 0:
                lrMs[iside].append(m)
                lrBs[iside].append(b)
                lrWs[iside].append(wt)
                if dbglines:
                    result.append(segment)

    for iside, ms in enumerate(lrMs):
        side = 'Left' if iside==0 else 'Right'
        if len(ms):
            avgm = np.average(lrMs[iside], weights=lrWs[iside])
            avgb = np.average(lrBs[iside], weights=lrWs[iside])
            outliers = []
            for ipop, m in enumerate(ms):
                if abs(m-avgm)/(m+avgm)*.5 > .15:
                    outliers.append(ipop)
                    if dbg:
                        print(side, 'm outlier (vs. lines avg) removed.', m, ', off by:', abs(m-avgm)/(m+avgm)*.5, ', len:', lrWs[iside][ipop])
## didn't help, seems same as w/o prvm. Tried varing the percentage diff, no use:
#                 if prvm and abs(m-prvm)/(m+prvm)*.5 > .15:
#                     outliers.append(ipop)
#                     if dbg:
#                         print(side, 'm outlier (vs. prv frames) removed.', m, ', off by:', abs(m-prvm)/(m+prvm)*.5, ', len:', lrWs[iside][ipop])
#                 elif abs(m-avgm)/(m+avgm)*.5 > .15:
#                     outliers.append(ipop)
#                     if dbg:
#                         print(side, 'm outlier (vs. lines avg) removed.', m, ', off by:', abs(m-avgm)/(m+avgm)*.5, ', len:', lrWs[iside][ipop])
## made it worst:
#             for ipop, b in enumerate(lrBs[iside]):
#                 if prvb and abs(b-prvb)/(b+prvb)*.5 > .8:
#                     if ipop not in outliers:
#                         outliers.append(ipop)
#                     if dbg:
#                         print(side, 'b outlier (vs. prv frames) removed.', b, ', off by:', abs(b-prvb)/(b+prvb)*.5, ', len:', lrWs[iside][ipop])
#                 elif abs(avgb-b)/(b+avgb)*.5 > .8:
#                     if ipop not in outliers:
#                         outliers.append(ipop)
#                     print(side, 'b outlier (vs. lines avg) removed.', b, ', off by:', abs(b-avgb)/(b+avgb)*.5, ', len:', lrWs[iside][ipop])
            if len(outliers):
                for ipop in sorted(outliers, reverse=True):
                    lrWs[iside].pop(ipop)
                    lrMs[iside].pop(ipop)
                    lrBs[iside].pop(ipop)
                if not len(lrWs[iside]):
                    print(side, ': No lines detected')
                    continue
                avgm = np.average(lrMs[iside], weights=lrWs[iside])
                avgb = np.average(lrBs[iside], weights=lrWs[iside])
            if dbg:
                print(side, ' lines:', len(ms))            
            x0 = abs((avgb - yclip)//avgm)
            x1 = abs((avgb - ylen-1)//avgm)
            result.append(np.array([[x0, yclip, x1, ylen-1]], dtype=np.int32))
        else:
            print(side, ': No lines detected')
    return [result, avgm, avgb]

prvMs = []
prvBs = []
prvFrames = 3

def process_image(image, return_list=False, dbg=False):
    ''' Returns (color) image with lane lines drawn
    dbg: to pass to lane_lines()
    return_list: returns list of [processed_image, canny_image] if True
    '''
    img_gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY) # BGR2GRAY if via cv2.imread()
    edge_img = canny(img_gray)
    masked_edge_img = mask_ROI(edge_img)
    line_segments = hough_lines(masked_edge_img)
    
    prvm = np.average(prvMs) if len(prvMs) >= prvFrames else 0
    prvb = np.average(prvBs) if len(prvBs) >= prvFrames else 0
    [lines, avgm, avgb] = lane_lines(line_segments, image.shape[0], prvm, prvb, dbg)
    lines_img = draw_lines(image, lines, multicolors=False)#True)
    result = weighted_img(lines_img, image) 
    
    prvMs.append(avgm)
    prvBs.append(avgb)
    if len(prvMs) > prvFrames:
        prvMs.pop(0)
        prvBs.pop(0)
    return [result, edge_img] if return_list else result
