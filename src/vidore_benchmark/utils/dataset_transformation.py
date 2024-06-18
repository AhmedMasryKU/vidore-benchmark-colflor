import os
import random

from datasets import Dataset, DatasetDict, concatenate_datasets, load_dataset

USE_LOCAL_DATASET = os.environ.get("USE_LOCAL_DATASET", "1") == "1"


def add_metadata_column(dataset, column_name, value):
    def add_source(example):
        example[column_name] = value
        return example

    return dataset.map(add_source)


def load_docvqa_dataset() -> DatasetDict:
    if USE_LOCAL_DATASET:
        dataset_doc = load_dataset("./data_dir/DocVQA", "DocVQA", split="validation")
        dataset_doc_eval = load_dataset("./data_dir/DocVQA", "DocVQA", split="test")
        dataset_info = load_dataset("./data_dir/DocVQA", "InfographicVQA", split="validation")
        dataset_info_eval = load_dataset("./data_dir/DocVQA", "InfographicVQA", split="test")
    else:
        dataset_doc = load_dataset("lmms-lab/DocVQA", "DocVQA", split="validation")
        dataset_doc_eval = load_dataset("lmms-lab/DocVQA", "DocVQA", split="test")
        dataset_info = load_dataset("lmms-lab/DocVQA", "InfographicVQA", split="validation")
        dataset_info_eval = load_dataset("lmms-lab/DocVQA", "InfographicVQA", split="test")

    # concatenate the two datasets
    dataset = concatenate_datasets([dataset_doc, dataset_info])
    dataset_eval = concatenate_datasets([dataset_doc_eval, dataset_info_eval])
    # sample 100 from eval dataset
    dataset_eval = dataset_eval.shuffle(seed=42).select(range(200))

    # rename question as query
    dataset = dataset.rename_column("question", "query")
    dataset_eval = dataset_eval.rename_column("question", "query")

    # create new column image_filename that corresponds to ucsf_document_id if not None, else image_url
    dataset = dataset.map(
        lambda x: {"image_filename": x["ucsf_document_id"] if x["ucsf_document_id"] is not None else x["image_url"]}
    )
    dataset_eval = dataset_eval.map(
        lambda x: {"image_filename": x["ucsf_document_id"] if x["ucsf_document_id"] is not None else x["image_url"]}
    )

    ds_dict = DatasetDict({"train": dataset, "test": dataset_eval})

    return ds_dict


def load_manu_embeddings() -> DatasetDict:
    dataset = load_dataset("manu/embedding_data_v2_100k", split="train")
    # transform dataset: text1 -> question, text2 -> document
    dataset = dataset.rename_column("text1", "query")
    dataset = dataset.rename_column("text2", "doc")

    # separate into train and test set. test set has 200 samples
    # shuffle
    dataset = dataset.shuffle(seed=42)
    dataset_eval = dataset.select(range(200))
    dataset = dataset.select(range(200, len(dataset)))
    ds_dict = DatasetDict({"train": dataset, "test": dataset_eval})
    return ds_dict


def load_tabfquad_retrieving() -> DatasetDict:
    if USE_LOCAL_DATASET:
        dataset = load_dataset("./data_dir/tabfquad_retrieving", split="train")
    else:
        dataset = load_dataset("coldoc/tabfquad_retrieving", split="test")
    # list unique image_filenames
    image_filenames = list(set(dataset["image_filename"]))

    # sample 200 image_filenames to create a test set
    image_filenames_eval = random.sample((list(image_filenames)), 70)
    # create test set
    dataset_eval = (
        dataset.filter(lambda x: x["image_filename"] in image_filenames_eval).shuffle(seed=42).select(range(200))
    )
    # create train set
    dataset = dataset.filter(lambda x: x["image_filename"] not in image_filenames_eval)
    # separate into train and test set. test set has 200 samples
    ds_dict = DatasetDict({"train": dataset, "test": dataset_eval})
    return ds_dict


def load_cauldron_datasets() -> DatasetDict:
    # general visual question answering
    ds_doc = load_dataset("HuggingFaceM4/the_cauldron", "docvqa", split="train")
    ds_doc = add_metadata_column(ds_doc, "source", "docvqa")

    ds_info = load_dataset("HuggingFaceM4/the_cauldron", "infographic_vqa", split="train")
    ds_info = add_metadata_column(ds_info, "source", "infographic_vqa")

    # Table understanding
    ds_tab = load_dataset("HuggingFaceM4/the_cauldron", "tat_qa", split="train")
    ds_tab = add_metadata_column(ds_tab, "source", "tat_qa")

    # concatenate datasets
    dataset = concatenate_datasets([ds_doc, ds_info, ds_tab])
    # rename question as query
    dataset = dataset.rename_column("texts", "query")
    dataset = dataset.rename_column("images", "image")
    # generate train and test set
    dataset = dataset.shuffle(seed=42)
    dataset_eval = dataset.select(range(200))
    dataset = dataset.select(range(200, len(dataset)))

    ds_dict = DatasetDict({"train": dataset, "test": dataset_eval})

    return ds_dict


def load_train_set() -> DatasetDict:

    ds_paths = [
        "infovqa_train",
        "docvqa_train",
        "arxivqa_train",
        "tatdqa_train",
        "tabfquad_train_subsampled",
        "syntheticDocQA_government_reports_train",
        "syntheticDocQA_healthcare_industry_train",
        "syntheticDocQA_artificial_intelligence_train",
        "syntheticDocQA_energy_train",
    ]
    base_path = "./data_dir/" if USE_LOCAL_DATASET else "coldoc/"
    ds_tot = []
    for path in ds_paths:
        cpath = base_path + path
        ds = load_dataset(cpath, split="train")
        if "arxivqa" in path:
            # subsample 10k
            ds = ds.shuffle(42).select(range(10000))
        ds_tot.append(ds)

    dataset = concatenate_datasets(ds_tot)
    dataset = dataset.shuffle(seed=42)
    # split into train and test
    dataset_eval = dataset.select(range(500))
    dataset = dataset.select(range(500, len(dataset)))
    ds_dict = DatasetDict({"train": dataset, "test": dataset_eval})
    return ds_dict


class TestSetFactory:
    def __init__(self, dataset_path):
        self.dataset_path = dataset_path

    def __call__(self, *args, **kwargs):
        dataset = load_dataset(self.dataset_path, split="test")
        return dataset


def load_docvqa_test() -> Dataset:
    dataset = load_docvqa_dataset()["test"]
    return dataset.select(range(200))


if __name__ == "__main__":
    ds = TestSetFactory("coldoc/tabfquad_test_subsampled")()
    print(ds)
