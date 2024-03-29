# -*- coding: utf-8 -*-
"""
Created on Sun Apr 26 17:17:56 2020

@author: Aleksander Zagajewski
"""
import copy

import matplotlib.pyplot as plt
from mrcnn import utils

import os, sys

import numpy as np
import sklearn.metrics
import skimage.io
from itertools import chain

def dircounter(folder):
    '''
    Return number of directories downstream of folder, recursively.

    Parameters
    ----------
    folder : str
        Path to top.

    Returns
    -------
    counter : int
        Total dirs.

    '''

    import os
    counter = 0

    if not isinstance(folder,list):
        folder = [folder]

    for root, dirs, files in chain.from_iterable(os.walk(path) for path in folder):
            counter = counter + 1
    return counter 

def filecounter(folder):
    '''
    Return total number of files downstream of folder, recursively.

    Parameters
    ----------
    folder : str
        Path to top.

    Returns
    -------
    counter : int
        Total files.

    '''

    import os

    if not isinstance(folder, list):
        folder = [folder]

    counter = 0
    for root, dirs, files in chain.from_iterable(os.walk(path) for path in folder):
        for file in files:
            counter = counter + 1
    return counter 

def interspread(iterable, separator):
    
    '''
    Interspread iterable with separator between iterations.

    Parameters
    ----------
    iterable : array-like. Use strings.
        List of strings to be interspread
    separator : string
        Separator to interspread with.

    Returns
    ------
    output : array-like.
        string of iterable with separator interspread
    '''
    
    def interspread_gen(iterable, separator):
        it = iter(iterable)
        yield next(it)
        for x in it:
            yield separator
            yield x

    generator = interspread_gen(iterable, separator)

    output = ''
    while True:
        try:
            st = next(generator)
            output = output + st
        except StopIteration:
            return output


def makedir(path):  # Make directory if it doesn't exist yet.
    import os
    if not os.path.isdir(path):
        os.mkdir(path)


def get_parent_path(n):  # Generate correct parent directory, n levels up cwd. Useful for robust relative imports on different OS. 0 is the current cwd parent, 1 is the parent of the parent, etc
    import os
    assert n >= 0
    cwd = os.getcwd()
    parent = os.path.abspath(cwd)
    for order in range(0, n, 1):
        parent = os.path.dirname(parent)
    return (parent)


def im_2_uint16(image):  # Rescale and convert image to uint16.
    assert len(image.shape) == 2, 'Image must be 2D matrix '
    import numpy

    img = image.copy()  # Soft copy problems otherwise

    img = img - img.min()  # rescale bottom to 0
    img = img / img.max()  # rescale top to 1
    img = img * 65535  # rescale (0,1) -> (0,65535)
    img = numpy.around(img)  # Round
    img = img.astype('uint16')

    return img

def print_cm(cm, labels, hide_zeroes=False, hide_diagonal=False, hide_threshold=None):
    """pretty print for confusion matrixes"""
    columnwidth = max([len(x) for x in labels] + [5])  # 5 is value length
    empty_cell = " " * columnwidth

    # Begin CHANGES
    fst_empty_cell = (columnwidth - 3) // 2 * " " + "t/p" + (columnwidth - 3) // 2 * " "

    if len(fst_empty_cell) < len(empty_cell):
        fst_empty_cell = " " * (len(empty_cell) - len(fst_empty_cell)) + fst_empty_cell
    # Print header
    print("    " + fst_empty_cell, end=" ")
    # End CHANGES

    for label in labels:
        print("%{0}s".format(columnwidth) % label, end=" ")

    print()
    # Print rows
    for i, label1 in enumerate(labels):
        print("    %{0}s".format(columnwidth) % label1, end=" ")
        for j in range(len(labels)):
            cell = "%{0}.1f".format(columnwidth) % cm[i, j]
            if hide_zeroes:
                cell = cell if float(cm[i, j]) != 0 else empty_cell
            if hide_diagonal:
                cell = cell if i != j else empty_cell
            if hide_threshold:
                cell = cell if cm[i, j] > hide_threshold else empty_cell
            print(cell, end=" ")
        print()


def class_id_to_name(dataset, ID):
    info = dataset.class_info
    for elm in info:
        id = elm['id']
        name = elm['name']
        if id == ID:
            return name
    raise ValueError('ID not found in dataset.')


def compute_pixel_metrics(dataset, image_ids, results):  # Custom function.

    print('Class ID and class name mappings...\n')
    print(dataset.class_info)
    print('')

    print('Pixelwise stats per image in test set...\n')

    gt_accumulator = np.asarray([], dtype='int')  # 1D arrays to store all pixels classifications throughout whole dataset
    pred_accumulator = np.asarray([], dtype='int')

    for image_id in image_ids:

        gt_mask, gt_class_id = dataset.load_mask(image_id)

        (x, y, _) = gt_mask.shape  # extract shape
        gt_composite = np.zeros((x, y))
        pred_composite = np.zeros((x, y))

        for unique_class_id in np.unique(gt_class_id):
            idx = [i for i, cls in enumerate(gt_class_id) if cls == unique_class_id]  # Find matching indicies
            gt_masks_perclass = gt_mask[:,:,idx]  # extract masks per class
            pred_masks_perclass = results[0]['masks']

            assert ((gt_masks_perclass == 0) | (gt_masks_perclass == 1)).all()  # Assert masks are strictly binary
            assert ((pred_masks_perclass == 0) | (pred_masks_perclass == 1)).all()

            gt_sum = np.sum(gt_masks_perclass,
                            axis=2)  # Collapse instance masks into one mask of all instances of class
            pred_sum = np.sum(pred_masks_perclass, axis=2)

            gt_sum[gt_sum > 1] = 1  # Overlapping masks will produce summations >1. Threshold.
            pred_sum[pred_sum > 1] = 1

            gt_composite = gt_composite + gt_sum * unique_class_id  # Encode class into composite by CID
            pred_composite = pred_composite + pred_sum * unique_class_id

        gt_accumulator = np.append(gt_accumulator,gt_composite.flatten())  # Store across all images
        pred_accumulator = np.append(pred_accumulator,pred_composite.flatten())


    # Plot confusion matrix over all images
    label_names = [class_id_to_name(dataset, id) for id in np.unique(gt_accumulator)]
    cmat_total = sklearn.metrics.confusion_matrix(gt_accumulator.flatten(), pred_accumulator.flatten(), labels=np.unique(gt_accumulator), normalize='true')

    disp = sklearn.metrics.ConfusionMatrixDisplay(cmat_total, display_labels=label_names)
    disp.plot()
    plt.show()


def get_ax(rows=1, cols=1, size=16):
    """Return a Matplotlib Axes array to be used in
    all visualizations in the notebook. Provide a
    central point to control graph sizes.

    Adjust the size attribute to control how big to render images
    """
    fig, ax = plt.subplots(rows, cols, figsize=(size * cols, size * rows))
    return ax


def image_stats(image_id, dataset):
    """Returns a dict of stats for one image."""
    image = dataset.load_image(image_id)
    mask, _ = dataset.load_mask(image_id)
    bbox = utils.extract_bboxes(mask)
    # Sanity check
    assert mask.shape[:2] == image.shape[:2]
    # Return stats dict
    return {
        "id": image_id,
        "shape": list(image.shape),
        "bbox": [[b[2] - b[0], b[3] - b[1]]
                 for b in bbox
                 # Uncomment to exclude nuclei with 1 pixel width
                 # or height (often on edges)
                 # if b[2] - b[0] > 1 and b[3] - b[1] > 1
                 ],
        "color": np.mean(image, axis=(0, 1)),
    }

def fetch_image(image_dir, filename):
    #Fetch image matching filename with recursive search down from image_dir

    matched_image = False

    for root, dirs, files in os.walk(image_dir):
        for file in files:
            if file == filename:
                if not matched_image: #If more than one match throw error

                    matched_image = True

                    if dirs != []:
                        path = os.path.join(root, dirs, file)
                    else:
                        path = os.path.join(root, file)

                    image = skimage.io.imread(path)

                else:
                    raise TypeError('More than one image matching filename found')

    return image

def summarize_triplet_loss(history, plot_title):
    '''Loss plotter suitable for similarity model training.'''


    fig, axs = plt.subplots(7, 1,figsize=(3*3,5*3))
    fig.suptitle(plot_title, y=1.05)

    #fig.subplots_adjust(top=0.65)

    # plot loss
    axs[0].set_title(plot_title)
    axs[0].plot(history['triplet_semihard_loss'], color='blue', label='train')
    axs[0].plot(history['val_triplet_semihard_loss'], color='orange', label='validation')
    axs[0].set_xlabel('Epoch')
    axs[0].set_ylabel('Semihard Triplet Loss')
    axs[0].legend(loc="upper right")

    axs[1].plot(history['triplet_hard_loss'], color='blue', label='train')
    axs[1].plot(history['val_triplet_hard_loss'], color='orange', label='validation')
    axs[1].set_xlabel('Epoch')
    axs[1].set_ylabel('Hard Triplet Loss')
    axs[1].legend(loc="upper left")

    axs[2].plot(history['mean2mean'], color='blue', label='train')
    axs[2].plot(history['val_mean2mean'], color='orange', label='validation')
    axs[2].set_xlabel('Epoch')
    axs[2].set_ylabel('Mean2Mean')
    axs[2].legend(loc="upper left")

    axs[3].plot(history['WT2WT_mean'], color='blue', label='train')
    axs[3].plot(history['val_WT2WT_mean'], color='orange', label='validation')
    axs[3].set_xlabel('Epoch')
    axs[3].set_ylabel('WT2WT')
    axs[3].legend(loc="upper right")

    axs[4].plot(history['CIP2CIP_mean'], color='blue', label='train')
    axs[4].plot(history['val_CIP2CIP_mean'], color='orange', label='validation')
    axs[4].set_xlabel('Epoch')
    axs[4].set_ylabel('CIP2CIP')
    axs[4].legend(loc="upper right")

    axs[5].plot(history['WT2CIP_mean'], color='blue', label='train')
    axs[5].plot(history['val_WT2CIP_mean'], color='orange', label='validation')
    axs[5].set_xlabel('Epoch')
    axs[5].set_ylabel('WT2CIP')
    axs[5].legend(loc="upper left")

    axs[6].plot(history['CIP2WT_mean'], color='blue', label='train')
    axs[6].plot(history['val_CIP2WT_mean'], color='orange', label='validation')
    axs[6].set_xlabel('Epoch')
    axs[6].set_ylabel('CIP2WT')
    axs[6].legend(loc="upper left")


    fig.tight_layout()
    plt.show()

def summarize_diagnostics(history, plot_title):
    '''Loss and accuracy plotter suitable for '''

    fig, axs = plt.subplots(2, 1)
    fig.suptitle(plot_title, y=1.05)

    fig.subplots_adjust(top=0.65)

	# plot loss
    axs[0].set_title(plot_title)
    axs[0].plot(history.history['loss'], color='blue', label='train')
    axs[0].plot(history.history['val_loss'], color='orange', label='validation')
    axs[0].set_xlabel('Epoch')
    axs[0].set_ylabel('Cross Entropy Loss')
    axs[0].legend(loc="upper right")
    # plot accuracy
    axs[1].set_title('Classification Accuracy')
    axs[1].plot(history.history['acc'], color='blue', label='train')
    axs[1].plot(history.history['val_acc'], color='orange', label='validation')
    axs[1].set_xlabel('Epoch')
    axs[1].set_ylabel('Accuracy')
    axs[1].legend(loc="lower right")

    fig.tight_layout()
    plt.show()


def remove_edge_cells(segmentations):
    '''Takes in a list of segmentations as produced by MRCNN. Remove all edge detections'''
    output = []
    total_removed = 0
    for img_segmentation in segmentations:
        (sy,sx,n) = img_segmentation['masks'].shape

        rois = img_segmentation['rois']

        (y1,x1,y2,x2) = rois[:,0], rois[:,1], rois[:,2], rois[:,3]

        #Find bboxes that are on image boundary
        boolmap = ~(y1==0) * ~(y1>=sy) * ~(y2==0) * ~(y2>=sy) * ~(x1==0) * ~(x1>=sx) * ~(x2==0) * ~(x2>=sx)

        idx = np.where(boolmap)[0]

        #print('Removing {}/{} cells on image boundary'.format(n-len(idx),n))

        update = {'rois':rois[idx,:], 'class_ids':img_segmentation['class_ids'][idx], 'scores':img_segmentation['scores'][idx], 'masks':img_segmentation['masks'][:,:,idx]}

        new_segmentation = copy.deepcopy(img_segmentation)
        new_segmentation.update(update)
        output.append(new_segmentation)
        total_removed += n-len(idx)
    return output, total_removed


def inspect_model_data(X, y, n):

    import matplotlib.pyplot as plt
    import skimage, skimage.exposure

    # Find indexes matching each label type

    uniques = np.unique(y, axis=0)  # Get unique labels
    class_count = len(uniques)  # Get total classes

    samples = len(n)

    fig, axs = plt.subplots(class_count, samples,constrained_layout=True, figsize=(samples*2,class_count*2))

    # Select samples from each category, either randomly or from supplied index
    for i, unique_y in enumerate(uniques):

        idx = np.asarray([i for i,value in enumerate(y) if (value == unique_y).all()]) #Select indicies matching each unique label

        # Index with n
        selection = idx[n]

        if isinstance(X,np.ndarray): # Select images by index
            imgs = X[selection,:,:,:]
        elif isinstance(X,list):
            imgs = [X[i] for i in selection]
        else:
            raise TypeError

        for j in range(0,len(selection),1):
            img = imgs[j]

            #Stretch contrast
            #p2, p98 = np.percentile(img, (2, 98))
            #img = skimage.exposure.rescale_intensity(img, in_range=(p2, p98))

            img = skimage.img_as_ubyte(img)  # Recast for imshow
            title = 'Label: ' + str(unique_y)
            axs[i, j].imshow(img)
            axs[i, j].set_title(title)

    fig.set_constrained_layout_pads(hspace=0.1, wspace=0.1)
    plt.show()

