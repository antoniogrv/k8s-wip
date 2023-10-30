from typing import List

from tqdm import tqdm
from glob import glob
import pandas as pd
import os

from Bio import SeqIO
from Bio import SeqRecord


def gt_shredder(
        transcript_dir: str,
        output_dir: str,
        len_read: int,
) -> None:
    # for each fastq files inside transcript dir
    files_paths: List[str] = glob(os.path.join(transcript_dir, '*fastq'))
    for file_path in tqdm(files_paths, total=len(files_paths), desc='Executing gt-shredder...'):
        file_name: str = os.path.basename(file_path)
        gene_name: str = file_name[:file_name.index('.fastq')]
        reads_file_name: str = f'{gene_name}.reads'
        reads_file_path: str = os.path.join(output_dir, reads_file_name)
        # init command
        command: str = f'gt shredder ' \
                       f'-minlength {len_read} ' \
                       f'-maxlength {len_read} ' \
                       f'-overlap 0 ' \
                       f'-clipdesc no ' \
                       f'{file_path} > {reads_file_path}'
        # execute gt-shredder
        os.system(command)
        # remove generated files
        for file_ext in ['.sds', '.ois', '.md5', '.esq', '.des', '.ssp']:
            os.system(f'rm {file_path}{file_ext}')


def fusion_simulator(
        fasta_format_path: str,
        text_format_path: str,
        n_fusions: int,
        genes_list: List[str],
        fusim_simulator_dir: str,
) -> None:
    # for each gene in genes panel
    for gene in tqdm(genes_list, desc=f'Executing fusim...', total=len(genes_list)):
        genes_list_tmp: List[str] = genes_list.copy()
        genes_list_tmp.remove(gene)
        # init command
        command: str = f'java -jar {os.path.join(fusim_simulator_dir, "fusim.jar")} ' \
                       f'-g {os.path.join(fusim_simulator_dir, "refFlat.txt")} ' \
                       f'-r {os.path.join(fusim_simulator_dir, "hg19.fa")} ' \
                       f'-f {fasta_format_path.format(gene=gene)}_tmp ' \
                       f'-t {text_format_path.format(gene=gene)} ' \
                       f'-n {n_fusions} ' \
                       f'-1 {gene} ' \
                       f'-2 {",".join(genes_list_tmp)} ' \
                       f'--cds-only ' \
                       f'--auto-correct-orientation 2>/dev/null'
        # execute command
        os.system(command)

        # add a number to the transcript identifier
        fasta_output_tmp_file = SeqIO.parse(open(f'{fasta_format_path.format(gene=gene)}_tmp'), 'fasta')
        fasta_output_file = open(f'{fasta_format_path.format(gene=gene)}', 'w')
        for idx, transcript_tmp in enumerate(fasta_output_tmp_file):
            transcript: SeqRecord = transcript_tmp
            transcript.id = f'{idx}_{transcript.id}'
            SeqIO.write(transcript, fasta_output_file, 'fasta')
        # close all files and remove tmp file
        fasta_output_file.close()
        os.system(f'rm {fasta_format_path.format(gene=gene)}_tmp')


def art_illumina(
        len_read: int,
        fusim_fasta_format_path: str,
        art_base_format_path: str,
        genes_list: List[str]
) -> None:
    for gene in tqdm(genes_list, desc=f'Generation reads with ART Illumina...', total=len(genes_list)):
        # init command
        command: str = f'art_illumina -i {fusim_fasta_format_path.format(gene=gene)} ' \
                       f'-l {len_read} ' \
                       f'-f 10 ' \
                       f'-p ' \
                       f'-m 400 ' \
                       f'-s 10 ' \
                       f'-o {art_base_format_path.format(gene=gene)} 1>/dev/null'
        # execute ART Illumina
        os.system(command)


def generate_reads(
        len_read: int,
        fusim_text_format_path: str,
        art_base_format_path: str,
        genes_list: List[str]
) -> pd.DataFrame:
    # init dataset
    dataset: pd.DataFrame = pd.DataFrame()
    columns: List[str] = ['read', 'gene_1', 'gene_2', 'strand', 'breakpoint']
    # execute ART on all file generated by Fusion Simulator
    for gene in tqdm(genes_list, desc=f'Generation of the chimeric and non-chimeric reads...', total=len(genes_list)):
        for idx_file in range(1, 3):
            # opening ART and fusim output files
            art_aln_output_file = open(f'{art_base_format_path.format(gene=gene)}{idx_file}.aln', 'r')
            art_fq_output_file = SeqIO.parse(open(f'{art_base_format_path.format(gene=gene)}{idx_file}.fq'), 'fastq')
            fusim_text_output_file = open(fusim_text_format_path.format(gene=gene), 'r')
            # skip this gne if there isn't transcripts generated
            if fusim_text_output_file.tell() == os.fstat(fusim_text_output_file.fileno()).st_size:
                continue
            # skip header lines
            while next(art_aln_output_file).strip() != '##Header End':
                pass
            next(fusim_text_output_file)

            # for each transcript in aln output file
            idx_transcript: int = 0
            for art_aln_line in art_aln_output_file:
                # get information of 1st gene name and 2nd gene name of starting transcript
                gene_1_fusion_information: List[str] = fusim_text_output_file.readline().split('\t')
                gene_2_fusion_information: List[str] = fusim_text_output_file.readline().split('\t')
                name_1_transcript: str = gene_1_fusion_information[2]
                name_2_transcript: str = gene_2_fusion_information[2]
                # create the transcript header
                transcript_header: str = f'>{idx_transcript}_ref|{name_1_transcript}-{name_2_transcript}'
                idx_transcript += 1

                # I need to check whether the transcript I am analyzing was used to create one
                # or more reads or whether it was skipped
                read_identification_list: List[str] = art_aln_line.split('\t')
                read_header: str = read_identification_list[0]
                while transcript_header != read_header:
                    # skip this transcript: two lines in the text file
                    gene_1_fusion_information: List[str] = fusim_text_output_file.readline().split('\t')
                    gene_2_fusion_information: List[str] = fusim_text_output_file.readline().split('\t')
                    name_1_transcript: str = gene_1_fusion_information[2]
                    name_2_transcript: str = gene_2_fusion_information[2]
                    # create the transcript header
                    transcript_header: str = f'>{idx_transcript}_ref|{name_1_transcript}-{name_2_transcript}'
                    idx_transcript += 1

                # get len of first gene and second gene of this transcript
                len_gene_1: int = int(gene_1_fusion_information[6])
                len_gene_2: int = int(gene_2_fusion_information[6])
                len_transcript: int = len_gene_1 + len_gene_2
                # get information of reads generated by this transcript
                n_reads: int = int(int(read_identification_list[1][len(read_header):(-4 if idx_file == 1 else -2)]) / 2)
                # iterate all reads generated by this transcript
                for idx in range(n_reads):
                    # get information of strand
                    strand: str = read_identification_list[3].strip()
                    # get index of start and finish of read inside the transcript
                    start_index: int = int(read_identification_list[2])
                    # whether the generated read is the reverse and complement of the source read
                    if strand == '-':
                        start_index: int = len_transcript - start_index - len_read
                    end_index: int = start_index + len_read
                    # get value of 1-st gene and 2-nd gene of read and breakpoint
                    bp_breakpoint: int = 0
                    if start_index < len_gene_1:
                        gene_1: str = gene_1_fusion_information[1]
                        if end_index <= len_gene_1:
                            gene_2: str = gene_1_fusion_information[1]
                        # in fact, there is a fusion
                        else:
                            gene_2: str = gene_2_fusion_information[1]
                            bp_breakpoint = len_gene_1 - start_index + 1
                    else:
                        gene_1: str = gene_2_fusion_information[1]
                        gene_2: str = gene_2_fusion_information[1]
                    # get and check read
                    read: str = next(art_fq_output_file).seq.__str__()
                    if len(read) != 150:
                        read: str = read[0:150]
                    # create row of dataset
                    row_dataset: pd.DataFrame = pd.DataFrame(
                        [[
                            read,
                            gene_1,
                            gene_2,
                            strand,
                            bp_breakpoint
                        ]], columns=columns
                    )
                    # append row on local dataset
                    dataset = pd.concat([dataset, row_dataset])
                    # skip line
                    for _ in range(2):
                        next(art_aln_output_file)
                    if idx + 1 < n_reads:
                        read_identification_list: List[str] = art_aln_output_file.readline().split('\t')

            # close Fusion Simulator output files
            art_aln_output_file.close()
            fusim_text_output_file.close()

    return dataset
