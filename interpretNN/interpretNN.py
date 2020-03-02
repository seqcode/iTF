import argparse
import numpy as np
from subprocess import call

# Import from utils
from utils import load_bound_data
from utils import get_bound_data
from utils import get_random_sample_shuffled

# Importing from Keras
from keras.models import load_model

# joint embeddings
from joint_embeddings import get_embeddings, get_embeddings_low_mem
from joint_embeddings import plot_1d_chrom, plot_1d_seq
from joint_embeddings import plot_embeddings
from joint_embeddings import plot_embeddings_bound_only

# sequence
from sequence_interpretation import plot_multiplicity, plot_kmer_scores, plot_correlation, plot_dots
from sequence_interpretation import motifs_in_ns, second_order_motifs
from sequence_attribution import get_sequence_attribution
# chromatin
from chromatin_interpretation import scores_at_domains
from chromatin_interpretation import scores_at_states, seq_scores_at_states


def embed(datapath, model, input_data):
    """
    Loads the bound data & extracts the joint embeddings
    This function takes as input path to the input data, as well as a loaded model.
    The function extracts the network embeddings into the final logistic node.

    Parameters:
    datapath: path to the bound files.
    model: trained model
    input_data (tuple): Contains X (seq) and C (chromatin) tensors

    Returns: None
    Saves both the postive and negative embedding matrices to the defined outfile.
    """
    # Extract and save the embeddings of bound and unbound sets to file.
    embedding = get_embeddings(model, input_data)
    # Extract and save the embeddings of a random negative set
    unbound_input = get_random_sample_shuffled(datapath + '.shuffled')
    embedding_negative = get_embeddings_low_mem(model, unbound_input)

    # Creating the outfile
    out_path = datapath + '.figure3/'
    call(['mkdir', out_path])
    # Saving the embeddings to outfile
    np.savetxt(datapath + ".embedding.txt", embedding)
    np.savetxt(datapath + '.negative.embedding.txt', embedding_negative)

    # Plotting
    # Plot 2-D embeddings: Bound + Unbound Sites
    plot_embeddings(out_path, embedding, embedding_negative)
    # Plot 2-D embeddings: Bound only
    plot_embeddings_bound_only(out_path, embedding, embedding_negative)
    # Plot marginal 1D distributions:
    plot_1d_seq(out_path, embedding, embedding_negative)
    plot_1d_chrom(out_path, embedding, embedding_negative)


def interpret_sequence(datapath, model, no_of_cdata):
    """
    Params:

    This function takes as input:
    1. datapath or prefix to the data files. For example:
    If your data is stored as ~/group/Ascl1.fa
    Then, the datapath or prefix = ~/group/Ascl1
    2. trained model in '.hdf5' format.

    Output:

    This function stores all output files as well as figures in the
    directory defined as prefix' + '.figure4'. For example,
    If your prefix is ~/group/Ascl1.fa
    Then, the output location will be ~/group/Ascl1.figure4/
    """
    # Load the bound data
    input_data = load_bound_data(datapath)
    # Get the sequence and chromatin attributions
    # Create a sub-folder to store all output figures from this function.
    out_path = datapath + '.figure4/'
    call(['mkdir', out_path])
    # Pass this sub_folder as the target destination for all plots/files generated here
    # This function is currently modified to return grads and grads_star_input

    grad, grad_star_inp = get_sequence_attribution(datapath, model, input_data, no_of_cdata)
    np.save(out_path + "gradients", grad)
    np.save(out_path + "gradients_star_inp", grad_star_inp)
    # rb_attribution = np.load(out_path + "sequence_attribution.npy")
    # visualize(datapath, out_path, input_data, rb_attribution)

    embedding = get_embeddings_low_mem(model, input_data)

    # Plot the observed 6-mer frequencies of CAGSTG kmers in Ascl1 sequences.
    print "Calculating the occurence of kmers at TF binding sites.."
    print "Calculating correlation with the sequence sub-network scores"
    outfile_a = out_path + 'Figure4C.pdf'
    outfile_b = out_path + 'Figure4D.pdf'
    motifs = ['CAGCTG', 'CACCTG', 'CAGGTG']  # motifs defined based on ChIP-seq data. Change based on TF.
    # Note: Since I am searching, explicitly adding the reverse complement here.
    plot_correlation(datapath, embedding, input_data, outfile_a, outfile_b, motifs)

    print 'Embedding multiple motif instances in sequences and calculating scores'
    outfile = out_path + 'Figure4E.pdf'
    no_of_repeats = 1000  # (For demonstration. For manuscript: no_of_repeats used = 1000)
    motif = 'CAGCTG'  # Using the most frequent motif here.
    plot_multiplicity(model, motif, outfile, no_of_repeats)

    # Embed all 10bp k-mers and aggregate second-order effects over the first order 8bp k-mers.
    # Define the file_path here:
    scores_file = out_path + '10mer.kmer_scores.txt'
    outfile = out_path + 'Figure4F.pdf'
    # Make sure that the scores_file does not already exist, since the function uses file appending.
    call(['rm', scores_file])
    # Running
    print 'Calculating scores for simulated embeddings of the CAGSTG kmer + 2bp flanks'
    motifs = ['CAGCTG', 'CACCTG']
    for motif in motifs:
        second_order_motifs(scores_file, model, motif=motif)
    print "Plotting scores at kmers + 2bp flanks"
    plot_kmer_scores(scores_file, outfile)

    # Embed all 8-mer/10-mer k-mers in a background of Ns
    print 'Calculating scores for simulated embeddings of the CAGSTG kmer + 1bp flanks'
    scores_file = out_path + '8mer.Ns.kmer_scores.txt'
    outfile = out_path + 'Figure4G.pdf'
    # Make sure that this file does not already exist, since the function uses file appending.
    call(['rm', outfile])
    for motif in motifs:
        motifs_in_ns(scores_file, model, motif=motif)
    print "Plotting scores at kmers + 1bp flanks"
    plot_dots(scores_file, outfile)


def interpret_chromatin(datapath, model):
    """
    Takes as input a model and the datapath to produce average
    chromatin score over domains.
    ----
    # Additional Requirements:
    # I need a file called datapath + '.domains'
    # This file should contain the domain calls mapped to the test chromosome
    # Currently, the domain caller used is in JAVA, so require a pre-processed file here.
    # This pre-processed file is loaded by the function itself.
    ----
    Produces a box plot in a sub-folder called datapath + Figure4
    Also, split the bedfiles based on chromatin scores
    """
    # Load the input data
    input_data = load_bound_data(datapath)
    # Specify the output directory
    out_path = datapath + '.figure5/'
    call(['mkdir', out_path])
    print "Calculating scores at chromatin input track domains.."
    scores_at_domains(model, datapath, out_path)
    # sum_heatmap(datapath, input_data, out_path)
    print "Calculating chromatin scores at chromHMM states"
    order = scores_at_states(model, datapath, out_path)
    print "Calculating sequence scores at chromHMM states"
    seq_scores_at_states(model, datapath, input_data, out_path, order)


def main():
    # TO DO:
    # SET UP AN EXAMPLE RUN SCRIPT/README
    parser = argparse.ArgumentParser(description="Characterize the sequence and chromatin\
                                             predictors of induced TF binding",
                                     prog='interpretNN')
    # adding parser arguments
    parser.add_argument("model", help="Input a trained model in '.hdf5' format")
    parser.add_argument("datapath", help="File path and prefix to the data files")
    parser.add_argument("numc", help="The number of input chromatin data tracks used for training")
    # no optional arguments added yet.
    parser.add_argument("--sequence", action='store_true', help="Interpret the sequence sub-network (Figures 4)")
    parser.add_argument("--chromatin", action='store_true', help="Interpret the chromatin sub-network (Figures 5")
    parser.add_argument("--joint", action='store_true', help="Plot the sequence-chromatin contributions (Figures 3)")
    args = parser.parse_args()

    # Load the model, as well as extract the bound data for the joint embeddings
    model = load_model(args.model)

    print 'Loading and extracting the subset of bound sites...'
    get_bound_data(args.datapath)
    print 'Done loading...'
    input_data = load_bound_data(args.datapath)

    if args.joint:
        # Load the bound data and extract the joint embeddings
        # Extract 2-D embedding for both bound data & shuffled (pre-made) unbound data
        # Need to alter this such the unbound data is done within this program.
        print 'Extracting the joint embeddings..'
        embed(args.datapath, model, input_data)

    # Making no changes here, this stays as is for now:
    if args.sequence:
        # sequence_attribution(args.datapath, model)
        print 'Calculating attribution and interpreting the sequence model...'
        interpret_sequence(args.datapath, model, args.numc)

    if args.chromatin:
        print 'Interpreting the chromatin model...'
        interpret_chromatin(args.datapath, model)


if __name__ == "__main__":
    main()
