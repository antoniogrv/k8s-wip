from model import MyModelConfig


class FCRecurrentNNConfig(MyModelConfig):
    def __init__(
            self,
            gene_classifier_name: str,
            gene_classifier_path: str,
            n_sentences: int,
            freeze: bool = True,
            hidden_size: int = 1024,
            rnn_type: str = 'lstm',
            n_rnn_layers: int = 1,
            dropout: float = 0.6,
            **kwargs
    ):
        # check pooling operation
        assert rnn_type in ['lstm']
        # call super class
        super().__init__(
            hyper_parameters={
                'gene_classifier_name': gene_classifier_name,
                'gene_classifier_path': gene_classifier_path,
                'n_sentences': n_sentences,
                'freeze': freeze,
                'hidden_size': hidden_size,
                'rnn_type': rnn_type,
                'n_rnn_layers': n_rnn_layers,
                'dropout': dropout
            },
            **kwargs
        )

    @property
    def gene_classifier_name(self) -> str:
        return self.hyper_parameters['gene_classifier_name']

    @property
    def gene_classifier_path(self) -> str:
        return self.hyper_parameters['gene_classifier_path']

    @property
    def n_sentences(self) -> int:
        return self.hyper_parameters['n_sentences']

    @property
    def freeze(self) -> bool:
        return self.hyper_parameters['freeze']

    @property
    def hidden_size(self) -> int:
        return self.hyper_parameters['hidden_size']

    @property
    def n_rnn_layers(self) -> int:
        return self.hyper_parameters['n_rnn_layers']

    @property
    def dropout(self) -> float:
        return self.hyper_parameters['dropout']

    @property
    def rnn_type(self) -> str:
        return self.hyper_parameters['rnn_type']
