import torch

class TrainingJob:
    def __init__(self, config, dataset):
        self.config = config
        self.dataset = config
        self.model = None

    """Job to train a model with a fixed set of hyperparemeters."""
    def create(config, dataset):
        """Factory method to create a training job and add necessary indexes to the
dataset (if not present)."""
        if config.raw['train']['type'] == '1toN':
            return TrainingJob1toN(config, dataset)
        else:
            raise ValueError("train.type")

    def run(self):
        self.config.log('Starting epoch')
        self.epoch()

    # TODO methods for checkpointing, logging, ...


class TrainingJob1toN(TrainingJob):

    def __init__(self, config, dataset):
        super(TrainingJob1toN,self).__init__(config, dataset)

        config.log("Initilizing 1-to-N training job")
        self.train_sp = dataset.indexes.get('train_sp')
        if not self.train_sp:
            self.train_sp = TrainingJob1toN._index(dataset.train[:,[0,1]], dataset.train[:,2])
            config.log("{} distinct sp pairs in train".format(len(self.train_sp)))
            dataset.indexes['train_sp'] = self.train_sp

        self.train_po = dataset.indexes.get('train_po')
        if not self.train_po:
            self.train_po = TrainingJob1toN._index(dataset.train[:,[1,2]], dataset.train[:,0])
            config.log("{} distinct po pairs in train".format(len(self.train_po)))
            dataset.indexes['train_po'] = self.train_po

        # TODO index dataset
        # create optimizers, losses, ... (partly in super?)

    def epoch(self):
        pass

    def _index(key, value):
        result = {}
        for i in range(len(key)):
            k = (key[i,0].item(), key[i,1].item())
            values = result.get(k)
            if values is None:
                values = []
                result[k] = values
            values.append(value[i])
        for key in result:
            result[key] = torch.IntTensor(sorted(result[key]))
        return result


        pass