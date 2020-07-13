import tensorflow as tf

class AdversarialAttack:
    def __init__(self, model, eps):
        """
        :param model: instance of tf.keras.Model that is used to generate adversarial examples with attack
        :param eps: float number - maximum perturbation size of adversarial attack
        """
        self.loss_obj = tf.keras.losses.SparseCategoricalCrossentropy()  # Loss that is used for adversarial attack
        self.model = model      # Model that is used for generating the adversarial examples
        self.eps = eps          # Threat radius of adversarial attack
        self.specifics = None   # String that contains all hyperparameters of attack
        self.name = None        # Name of the attack - e.g. FGSM


class Fgsm(AdversarialAttack):
    def __init__(self, model, eps):
        """
        :param model: instance of tf.keras.Model that is used for generating adversarial examples
        :param eps: floate number = maximum perturbation size in adversarial attack
        """
        super().__init__(model, eps)
        self.name = "FGSM"
        self.specifics = "FGSM - eps: {:.2f}".format(eps)

    def __call__(self, clean_images, true_labels):
        """
        :param clean_images: tf.Tensor - shape (n,h,w,c) - clean images that will be transformed to adversarial examples
        :param true_labels: tf.Tensor shape (n,) - true labels of clean images
        :return: tf.Tensor - shape (n,h,w,c) - adversarial examples generated with FGSM Attack
        """
        with tf.GradientTape(watch_accessed_variables=False) as tape:
            # Only gradient w.r.t clean_images is accumulated NOT w.r.t model parameters
            tape.watch(clean_images)
            prediction = self.model(clean_images)
            loss = self.loss_obj(true_labels, prediction)

        gradients = tape.gradient(loss, clean_images)
        perturbations = self.eps * tf.sign(gradients)

        adv_examples = clean_images + perturbations
        adv_examples = tf.clip_by_value(adv_examples, 0, 1)
        return adv_examples


class OneStepLeastLikely(AdversarialAttack):
    def __init__(self, model, eps):
        """
        :param model: instance of tf.keras.Model that is used to compute adversarial examples
        :param eps: float number - maximum perturbation size for adversarial attack
        """
        super().__init__(model, eps)
        self.name = "One Step Least Likely (Step 1.1)"
        self.specifics = "One Step Least Likely (Step 1.1) - eps: {:.2f}".format(eps)

    def __call__(self, clean_images):
        """
        :param clean_images: tf.Tensor - shape (n,h,w,c) - clean images that will be transformed to adversarial examples
        :return: tf.Tensor - shape (n,h,w,c) - adversarial examples generated with One Step Least Likely Attack
        """
        # Track gradients
        with tf.GradientTape(watch_accessed_variables=False) as tape:
            # only gradient w.r.t. clean_images is accumulated NOT w.r.t model parameters!
            tape.watch(clean_images)
            prediction = self.model(clean_images)
            # Compute least likely predicted label for clean_images
            y_ll = tf.math.argmin(prediction, 1)
            loss = self.loss_obj(y_ll, prediction)
        # Compute gradients of loss w.r.t clean_images
        gradients = tape.gradient(loss, clean_images)
        # Compute perturbation as step size times signum of gradients
        perturbation = self.eps * tf.sign(gradients)
        # Add perturbation to clean_images
        X = clean_images - perturbation
        # Make sure entries in X are between 0 and 1
        X = tf.clip_by_value(X, 0, 1)
        # Return adversarial exmaples
        return X


class BasicIter(AdversarialAttack):
    def __init__(self, model, eps, alpha, num_iter):
        """
        :param model: instance of tf.keras.Model that is used for generating adversarial examples
        :param eps:  float number - maximum perturbation size for adversarial attack
        :param alpha: float number - step size in adversarial attack
        :param num_iter: int number - number of iterations in adversarial attack
        """
        super().__init__(model, eps)
        self.alpha = alpha
        self.num_iter = num_iter
        self.name = "Basic Iterative Method"
        self.specifics = "Basic Iterative Method " \
                         "- eps: {:.2f} - alpha: {:.4f} " \
                         "- num_iter: {:d}".format(eps, alpha, num_iter)

    def __call__(self, clean_images, true_labels):
        """
        :param clean_images: tf.Tensor - shape (n,h,w,c) - clean images that will be transformed to adversarial examples
        :param true_labels: tf.Tensor - shape (n,) - true labels of clean images
        :return: tf.Tensor - shape (n,h,w,c) - adversarial examples generated with Basic Iterative Attack
        """
        # Start iterative attack and update X in each iteration
        X = clean_images
        for i in tf.range(self.num_iter):
            # Track gradients
            with tf.GradientTape(watch_accessed_variables=False) as tape:
                # Only gradients w.r.t. X are accumulated, NOT model parameters
                tape.watch(X)
                prediction = self.model(X)
                loss = self.loss_obj(true_labels, prediction)

            gradients = tape.gradient(loss, X)
            # Compute perturbation as step size times signum of gradients
            perturbation = self.alpha * tf.sign(gradients)
            # Update X by adding perturbation
            X = X + perturbation
            # Make sure X does not leave epsilon L infinity ball around clean_images
            X = tf.clip_by_value(X, clean_images - self.eps, clean_images + self.eps)
            # Make sure entries from X remain between 0 and 1
            X = tf.clip_by_value(X, 0, 1)
        # Return adversarial examples
        return X


class IterativeLeastLikely(AdversarialAttack):
    def __init__(self, model, eps, alpha, num_iter):
        """
        :param model: instance of tf.keras.Model model that is used to generate adversarial examples
        :param eps: float number - maximum perturbation size for adversarial attack
        :param alpha: float number - step size in adversarial attack
        :param num_iter: int number - number of iterations in adversarial attack
        """
        super().__init__(model, eps)
        self.alpha = alpha
        self.num_iter = num_iter
        self.name = "Iterative Least Likely (Iter 1.1)"
        self.specifics = "Iterative Least Likely (Iter 1.1) " \
                         "- eps: {:.2f} - alpha: {:.4f} " \
                         "- num_iter: {:d}".format(eps, alpha, num_iter)

    def __call__(self, clean_images):
        """
        :param clean_images: tf.Tensor - shape (n,h,w,c) - clean images that will be transformed to adversarial examples
        :return: tf.Tensor - shape (n,h,w,c) - adversarial examples generated with Iterative Least Likely Method
        """
        # Get least likely predicted class for clean_images
        prediction = self.model(clean_images)
        y_ll = tf.math.argmin(prediction, 1)
        # Start iterative attack and update X in each iteration
        X = clean_images
        for i in tf.range(self.num_iter):
            # Track gradients
            with tf.GradientTape(watch_accessed_variables=False) as tape:
                # Only gradients w.r.t. X are accumulated, NOT model parameters
                tape.watch(X)
                prediction = self.model(X)
                loss = self.loss_obj(y_ll, prediction)
            # Get gradients of loss w.r.t X
            gradients = tape.gradient(loss, X)
            # Compute perturbation as step size times signum of gradients
            perturbation = self.alpha * tf.sign(gradients)
            # Update X by adding perturbation
            X = X - perturbation
            # Make sure X does not leave epsilon L infinity ball around clean_images
            X = tf.clip_by_value(X, clean_images - self.eps, clean_images + self.eps)
            # Make sure entries from X remain between 0 and 1
            X = tf.clip_by_value(X, 0, 1)
        # Return adversarial examples
        return X


class RandomPlusFgsm(AdversarialAttack):
    def __init__(self, model, eps, alpha):
        """
        :param model: instance of tf.keras.Model that is used to generate adversarial examples
        :param eps: float number - maximum perturbation size for adversarial attack
        :param alpha: float numnber - step size in adversarial attack
        """
        super().__init__(model, eps)
        self.name = "Random Plus FGSM"
        self.specifics = "Random Plus FGSM - eps: {:.2f} - alpha: {:.4f}".format(eps, alpha)
        self.alpha = alpha

    def __call__(self, clean_images, true_labels):
        """
        :param clean_images: clean images that will be transformed into adversarial examples
        :param true_labels: true labels of clean_images
        :return: adversarial examples generated with Random Plus FGSM Attack
        """
        # Sample initial perturbation uniformly from interval [-epsilon, epsilon]
        random_delta = 2 * self.eps * tf.random.uniform(shape=clean_images.shape) - self.eps
        # Add random initial perturbation
        X = clean_images + random_delta
        # Track Gradients
        with tf.GradientTape(watch_accessed_variables=False) as tape:
            # Only gradient w.r.t clean_images is accumulated NOT w.r.t model parameters
            tape.watch(X)
            prediction = self.model(X)
            loss = self.loss_obj(true_labels, prediction)
        # Get gradients of loss w.r.t X
        gradients = tape.gradient(loss, X)
        # Compute pertubation as step size time signum gradients
        perturbation = self.alpha * tf.sign(gradients)
        # Update X by adding perturbation
        X = X + perturbation
        # Make sure adversarial examples does not leave epsilon L infinity ball around clean_images
        X = tf.clip_by_value(X, clean_images - self.eps, clean_images + self.eps)
        # Make sure entries remain between 0 and 1
        X = tf.clip_by_value(X, 0, 1)
        # Return adversarial examples
        return X